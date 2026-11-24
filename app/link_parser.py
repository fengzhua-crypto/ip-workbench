"""链接解析：本机 media-parser 服务 + 腾讯元宝登录态。

- media-parser 放在 tools\\media-parser，独立 venv，仅监听 127.0.0.1:8051。
- 视频号链接需要元宝 Cookie（hy_user / hy_token），登录一次后一直可用，过期再扫。
- 解析、下载都在本机进行；只有元宝接口请求经过腾讯服务器。
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config, db

ROOT = config.ROOT_DIR
PARSER_DIR = ROOT / "tools" / "media-parser"
PARSER_PY = PARSER_DIR / ".venv" / "Scripts" / "python.exe"
PARSER_DB = PARSER_DIR / "data" / "media_parser.db"
BASE = f"http://127.0.0.1:{os.environ.get('IPWB_PARSER_PORT', '8051')}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_state = {"status": "idle", "message": "", "at": ""}
_thread: threading.Thread | None = None
_proc: subprocess.Popen | None = None
_proc_lock = threading.Lock()


class LinkError(RuntimeError):
    """链接解析失败（服务未启动、未登录、Cookie 失效等）。"""


def _port_open() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(BASE.rsplit(":", 1)[1])), timeout=0.5):
            return True
    except OSError:
        return False


def ensure_server(timeout: float = 20) -> None:
    """media-parser 没启动就拉起来（独立进程，退出工作台后自动结束）。"""
    global _proc
    if _port_open():
        return
    if not PARSER_PY.exists():
        raise LinkError("链接解析服务还没安装（tools\\media-parser），请让助手先安装")
    with _proc_lock:
        if _port_open():
            return
        env = os.environ.copy()
        env["API_ONLY"] = "true"
        env["WEB_PORT"] = BASE.rsplit(":", 1)[1]
        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        _proc = subprocess.Popen(
            [str(PARSER_PY), "run_local.py"], cwd=str(PARSER_DIR), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open():
            return
        time.sleep(0.5)
    raise LinkError("链接解析服务启动失败")


def _parser_cookie_set() -> bool:
    if not PARSER_DB.exists():
        return False
    try:
        con = sqlite3.connect(str(PARSER_DB))
        row = con.execute(
            "SELECT value FROM system_settings WHERE key IN ('cookie_yuanbao','cookie_wechat_channels')"
        ).fetchone()
        con.close()
    except Exception:
        return False
    return bool(row and str(row[0]).strip())


def _save_cookie(cookie: str) -> None:
    PARSER_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(PARSER_DB))
    con.execute(
        "CREATE TABLE IF NOT EXISTS system_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    con.execute(
        "INSERT INTO system_settings(key, value) VALUES('cookie_yuanbao', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (cookie,),
    )
    con.commit()
    con.close()


def parse(url: str) -> dict:
    """解析分享链接，返回 media-parser 的 data 字段。"""
    ensure_server()
    query = urllib.parse.urlencode({"url": url})
    req = urllib.request.Request(f"{BASE}/api/v1/parse?{query}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            raise LinkError(f"解析服务返回 {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LinkError("连不上本机链接解析服务") from exc

    if not payload.get("succ") or payload.get("retcode") != 200:
        message = payload.get("retdesc") or "链接解析失败"
        if "YUANBAO_COOKIE" in message or "元宝" in message or "cookie" in message.lower():
            message = "视频号链接需要先在拆解页点「元宝登录」扫码，登录后再试"
        raise LinkError(message)
    data = payload.get("data") or {}
    if not data.get("video_url"):
        raise LinkError("解析成功但没拿到视频地址（可能是图文或链接已失效）")
    return data


def download(video_url: str, dest: Path, max_mb: int = 500) -> int:
    """把视频下载到本机，返回字节数。"""
    req = urllib.request.Request(video_url, headers={
        "User-Agent": UA,
        "Referer": "https://channels.weixin.qq.com/",
    })
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_mb * 1024 * 1024:
                    fh.close()
                    dest.unlink(missing_ok=True)
                    raise LinkError(f"视频超过 {max_mb}MB，已取消下载")
                fh.write(chunk)
    except urllib.error.HTTPError as exc:
        dest.unlink(missing_ok=True)
        raise LinkError(f"下载视频失败：HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        dest.unlink(missing_ok=True)
        raise LinkError("下载视频失败：网络中断") from exc
    if not size:
        dest.unlink(missing_ok=True)
        raise LinkError("下载视频失败：文件为空")
    return size


# ---------- 元宝扫码登录 ----------

def login_status() -> dict:
    return {**_state, "running": bool(_thread and _thread.is_alive()),
            "cookie_set": _parser_cookie_set(), "server": _port_open()}


def _set(status: str, message: str = "") -> None:
    _state.update({"status": status, "message": message, "at": db.now_iso()})


def _wait_cookies(ctx, timeout: int = 300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        except Exception:
            return None
        if cookies.get("hy_user") and cookies.get("hy_token"):
            return f"hy_user={cookies['hy_user']}; hy_token={cookies['hy_token']};"
        time.sleep(2)
    return None


def _login_run() -> None:
    global _thread
    try:
        from playwright.sync_api import sync_playwright

        _set("waiting", "请在弹出的浏览器里用微信扫码登录腾讯元宝")
        profile = config.DATA_DIR / "auth" / "yuanbao-profile"
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(profile), channel="chrome", headless=False,
                no_viewport=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                # 清掉旧 Cookie，强制出现扫码页，避免拿过期 Cookie 直接"成功"
                ctx.clear_cookies()
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto("https://yuanbao.tencent.com", wait_until="domcontentloaded", timeout=30000)
                cookie = _wait_cookies(ctx, timeout=300)
            finally:
                ctx.close()
        if cookie:
            _save_cookie(cookie)
            db.log_event("link.login_ok", {})
            _set("ok", "元宝登录成功，链接解析可以用了")
        else:
            _set("failed", "没有等到登录：窗口被关闭或超过 5 分钟")
    except Exception as exc:  # noqa: BLE001
        _set("failed", f"登录失败：{exc}")
    finally:
        _thread = None


def start_login() -> dict:
    global _thread
    if _thread and _thread.is_alive():
        return {"ok": False, "message": "已经在等待扫码"}
    _set("waiting", "正在打开浏览器…")
    _thread = threading.Thread(target=_login_run, name="yuanbao-login", daemon=True)
    _thread.start()
    return {"ok": True, "status": "waiting"}
