"""视频号助手后台数据同步。

用已保存的登录态（data\\auth\\chrome-profile）直接请求后台的数据接口，
不解析页面。每日同步的是"前一天"的完整数据。

单独运行：
    python -m app.channels_sync                 # 同步昨天
    python -m app.channels_sync 2026-11-11      # 同步指定日期
"""
from __future__ import annotations

import json
import threading
import time
from datetime import date, datetime, timedelta

from playwright.sync_api import sync_playwright

from . import config, db

BASE = "https://channels.weixin.qq.com"
PROFILE_DIR = config.DATA_DIR / "auth" / "chrome-profile"

PATHS = {
    "auth": "/cgi-bin/mmfinderassistant-bin/auth/auth_data",
    "fans": "/cgi-bin/mmfinderassistant-bin/statistic/fans_trend",
    "content": "/cgi-bin/mmfinderassistant-bin/statistic/new_post_total_data",
    "posts": "/micro/content/cgi-bin/mmfinderassistant-bin/post/post_list",
}

LOGIN_ERR_CODES = {-3, 1000, 200003, 300333, 300334, 301002}

_lock = threading.Lock()
_running = False


class LoginExpired(RuntimeError):
    """登录态失效，需要重新扫码。"""


def _now_ms() -> str:
    return str(int(time.time() * 1000))


def _day_ts(day: date) -> int:
    return int(datetime(day.year, day.month, day.day).timestamp())


def _post(ctx, key: str, body: dict) -> dict:
    resp = ctx.request.post(
        BASE + PATHS[key], data=json.dumps(body),
        headers={"Content-Type": "application/json"}, timeout=45000,
    )
    raw = resp.text()
    try:
        payload = json.loads(raw)
    except Exception:
        raise LoginExpired("后台返回的不是数据，可能登录已过期")
    code = payload.get("errCode")
    if code != 0:
        msg = payload.get("errMsg") or ""
        if code in LOGIN_ERR_CODES or "login" in str(msg).lower() or "登录" in str(msg):
            raise LoginExpired(msg or f"errCode={code}")
        raise RuntimeError(f"接口 {key} 返回 {code}：{msg}")
    return payload.get("data") or {}


def _range_body(day: date) -> dict:
    ts = _day_ts(day)
    return {"startTs": str(ts), "endTs": str(ts), "interval": 3, "timestamp": _now_ms()}


def _num(value) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _last(arr) -> int:
    if isinstance(arr, list) and arr:
        return _num(arr[-1])
    return 0


def _account(ctx) -> dict:
    data = _post(ctx, "auth", {"timestamp": _now_ms()})
    user = data.get("finderUser") or {}
    return {
        "nickname": user.get("nickname") or "",
        "finder_id": user.get("finderUsername") or "",
        "head_img": user.get("headImgUrl") or "",
    }


def _collect_posts(ctx, day: date, page_size: int = 50, max_pages: int = 40) -> dict:
    """翻遍作品列表，按"昨日阅读"找出最高的一条，并统计昨日阅读合计。"""
    best = {"play": 0, "title": "", "read_total": 0, "count": 0, "scanned": 0}
    for page in range(1, max_pages + 1):
        data = _post(ctx, "posts", {
            "pageSize": page_size, "currentPage": page,
            "userpageType": 11, "stickyOrder": False, "timestamp": _now_ms(),
        })
        items = data.get("list") or []
        total = _num(data.get("totalCount"))
        for item in items:
            best["scanned"] += 1
            reads = _num(item.get("yesterdayReadCount"))
            best["read_total"] += reads
            if reads > best["play"]:
                best["play"] = reads
                desc = item.get("desc") or {}
                best["title"] = (desc.get("description") or "").replace("\n", " ").strip()
        if not items or best["scanned"] >= total:
            break
    return best


def sync_day(day: date | None = None) -> dict:
    """同步某一天的数据并写入数据库，返回同步结果。"""
    day = day or (date.today() - timedelta(days=1))
    db.init_db()
    if not PROFILE_DIR.exists():
        raise LoginExpired("本机还没有登录过视频号后台")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            account = _account(ctx)
            fans = _post(ctx, "fans", _range_body(day))
            content = _post(ctx, "content", _range_body(day))
            posts = _collect_posts(ctx, day)
        finally:
            ctx.close()

    totals = content.get("totalData") or {}
    play = _last(totals.get("browse"))
    like = _last(totals.get("like"))
    comment = _last(totals.get("comment"))
    forward = _last(totals.get("forward"))
    fav = _last(totals.get("fav"))
    if not play and posts.get("read_total"):
        play = posts["read_total"]
    engagement = round((like + comment + forward + fav) / play * 100, 2) if play else 0.0

    metric = {
        "stat_date": day.isoformat(),
        "followers_total": _last(fans.get("total")),
        "followers_add": _last(fans.get("add")),
        "followers_del": _last(fans.get("reduce")),
        "followers_net": _last(fans.get("netAdd")),
        "play_total": play,
        "like_total": like,
        "comment_total": comment,
        "forward_total": forward,
        "fav_total": fav,
        "top_play": posts.get("play", 0),
        "top_title": posts.get("title", ""),
        "engagement_rate": engagement,
        "synced_at": db.now_iso(),
        "status": "ok",
        "raw": json.dumps({
            "account": account, "fans": fans, "content": totals, "posts": posts,
        }, ensure_ascii=False),
    }
    db.save_metric(metric)
    db.set_setting("account", account)
    db.set_setting("sync_state", {
        "status": "ok", "at": metric["synced_at"], "date": metric["stat_date"], "message": "",
    })
    db.log_event("sync.ok", {"date": metric["stat_date"], "play": play})
    return metric


def _run(date_text: str | None, background: bool = False) -> dict:
    global _running
    day = None
    if date_text:
        try:
            day = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            return {"ok": False, "status": "failed", "message": "日期格式应为 YYYY-MM-DD"}
    if not try_lock():
        return {"ok": False, "status": "running",
                "message": "另一个后台任务正在运行（同步或扫码），请稍候"}
    _running = True
    try:
        metric = sync_day(day)
        return {"ok": True, "status": "ok", "metric": metric}
    except LoginExpired as exc:
        state = {"status": "login_expired", "at": db.now_iso(),
                 "date": (day or date.today() - timedelta(days=1)).isoformat(),
                 "message": str(exc)}
        db.set_setting("sync_state", state)
        db.log_event("sync.login_expired", state)
        return {"ok": False, "status": "login_expired", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001
        state = {"status": "failed", "at": db.now_iso(),
                 "date": (day or date.today() - timedelta(days=1)).isoformat(),
                 "message": str(exc)}
        db.set_setting("sync_state", state)
        db.log_event("sync.failed", state)
        return {"ok": False, "status": "failed", "message": str(exc)}
    finally:
        _running = False
        unlock()


def try_lock() -> bool:
    """占用登录态目录（同一时间只允许一个浏览器任务）。"""
    return _lock.acquire(blocking=False)


def unlock() -> None:
    try:
        _lock.release()
    except RuntimeError:
        pass


def is_running() -> bool:
    return _running


def main() -> int:
    import sys

    day_text = sys.argv[1] if len(sys.argv) > 1 else None
    result = _run(day_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
