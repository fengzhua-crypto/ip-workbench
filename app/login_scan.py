"""扫码登录：在有界面的 Chrome 里打开视频号助手，等用户用微信扫码。

接口不阻塞：点"重新扫码"后后台线程打开浏览器，前端轮询 /api/login/status。
成功后保存账号信息、把同步状态重置为 pending，并把当日自动同步的重试次数清零。
同一个登录态目录只能开一个浏览器，所以整个扫码过程与同步共用一把锁。
"""
from __future__ import annotations

import threading
import time
from datetime import date, timedelta

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from . import channels_sync, db

LOGIN_URL = f"{channels_sync.BASE}/platform"
PROFILE_DIR = channels_sync.PROFILE_DIR
TIMEOUT_SECONDS = 300
POLL_SECONDS = 2

_state = {"status": "idle", "message": "", "at": ""}
_thread: threading.Thread | None = None


def status() -> dict:
    return {**_state, "running": bool(_thread and _thread.is_alive())}


def _set(status_text: str, message: str = "") -> None:
    _state.update({"status": status_text, "message": message, "at": db.now_iso()})


def _wait_login(ctx):
    """在浏览器里等扫码完成，返回账号信息；窗口被关或超时返回 None。"""
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            if not ctx.pages:
                return None
            account = channels_sync._account(ctx)
        except PlaywrightError:
            # 用户把窗口关掉了
            return None
        except Exception:  # 未登录时接口会报错，属正常，继续等
            account = None
        if account and account.get("nickname"):
            return account
        time.sleep(POLL_SECONDS)
    return None


def _run() -> None:
    global _thread
    if not channels_sync.try_lock():
        _set("failed", "另一个后台任务正在运行（同步或扫码），请稍候再试")
        _thread = None
        return
    try:
        _set("waiting", "请在弹出的 Chrome 窗口里用微信扫码登录")
        account = None
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR), channel="chrome", headless=False,
                no_viewport=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                account = _wait_login(ctx)
            finally:
                ctx.close()

        if account:
            db.set_setting("account", account)
            latest = db.latest_metric()
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if latest and latest["stat_date"] == yesterday:
                db.set_setting("sync_state", {
                    "status": "ok", "at": latest["synced_at"],
                    "date": latest["stat_date"], "message": "",
                })
            else:
                db.set_setting("sync_state", {
                    "status": "pending", "at": db.now_iso(), "date": "", "message": "",
                })
            sched = db.get_setting("scheduler", {}) or {}
            if (sched.get("date") == date.today().isoformat()
                    and sched.get("status") == "login_expired"):
                db.set_setting("scheduler", {**sched, "attempts": 0, "status": "login_renewed"})
            db.log_event("login.ok", {"finder_id": account.get("finder_id", "")})
            _set("ok", "登录成功")
        else:
            _set("failed", "没有等到扫码：窗口被关闭或超过 5 分钟。可以重新点一次")
    except Exception as exc:  # noqa: BLE001
        _set("failed", f"扫码失败：{exc}")
        db.log_event("login.failed", {"error": str(exc)})
    finally:
        channels_sync.unlock()
        _thread = None


def start() -> dict:
    global _thread
    if _thread and _thread.is_alive():
        return {"ok": False, "status": "waiting", "message": "已经在等待扫码，请查看弹出的浏览器窗口"}
    if channels_sync.is_running():
        return {"ok": False, "status": "busy", "message": "正在同步数据，请等同步结束后再扫码"}
    _set("waiting", "正在打开浏览器…")
    _thread = threading.Thread(target=_run, name="scan-login", daemon=True)
    _thread.start()
    return {"ok": True, "status": "waiting"}
