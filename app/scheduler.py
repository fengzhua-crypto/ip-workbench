"""每日自动同步：工作台运行时，到点自动同步前一天的数据。

默认每天 08:30，可用环境变量 IPWB_SYNC_TIME="HH:MM" 调整。
一天最多尝试 3 次，每次间隔 30 分钟；成功后不再重复。
"""
from __future__ import annotations

import threading
from datetime import date, datetime, timedelta

from . import channels_sync, config, db

_stop = threading.Event()
_thread: threading.Thread | None = None
MAX_ATTEMPTS = 3
RETRY_GAP_SECONDS = 30 * 60


def _parse_time(text: str) -> tuple[int, int]:
    try:
        hh, mm = text.split(":")
        return int(hh), int(mm)
    except Exception:
        return 8, 30


def _today() -> str:
    return date.today().isoformat()


def tick(now: datetime | None = None) -> str:
    """检查一次是否需要同步，返回一个状态词（便于观察和测试）。"""
    now = now or datetime.now()
    hh, mm = _parse_time(getattr(config, "SYNC_TIME", "08:30"))
    if (now.hour, now.minute) < (hh, mm):
        return "before_time"

    target = (now.date() - timedelta(days=1)).isoformat()
    if db.get_metric(target):
        return "already_done"
    if channels_sync.is_running():
        return "running"

    state = db.get_setting("scheduler", {}) or {}
    attempts = state.get("attempts", 0) if state.get("date") == _today() else 0
    if attempts >= MAX_ATTEMPTS:
        return "gave_up"

    last_at = state.get("at")
    if attempts and last_at:
        try:
            if (now - datetime.fromisoformat(last_at)).total_seconds() < RETRY_GAP_SECONDS:
                return "waiting_retry"
        except ValueError:
            pass

    result = channels_sync._run(None)
    db.set_setting("scheduler", {
        "date": _today(), "attempts": attempts + 1,
        "at": db.now_iso(), "status": result.get("status"),
    })
    return str(result.get("status"))


def _loop() -> None:
    while not _stop.is_set():
        try:
            tick()
        except Exception:  # noqa: BLE001
            pass
        _stop.wait(60)


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="daily-sync", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()


def status() -> dict:
    state = db.get_setting("scheduler", {}) or {}
    hh, mm = _parse_time(getattr(config, "SYNC_TIME", "08:30"))
    return {
        "enabled": bool(_thread and _thread.is_alive()),
        "time": f"{hh:02d}:{mm:02d}",
        "attempts": state.get("attempts", 0) if state.get("date") == _today() else 0,
        "last_status": state.get("status", ""),
        "last_at": state.get("at", ""),
    }
