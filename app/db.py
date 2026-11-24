"""SQLite 数据层：建表、迁移、演示数据。"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    platform    TEXT NOT NULL DEFAULT '视频号',
    author      TEXT NOT NULL DEFAULT '',
    url         TEXT NOT NULL DEFAULT '',
    file_name   TEXT NOT NULL DEFAULT '',
    file_path   TEXT NOT NULL DEFAULT '',
    file_size   INTEGER NOT NULL DEFAULT 0,
    duration    REAL NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'ready',
    transcript  TEXT NOT NULL DEFAULT '',
    meta        TEXT NOT NULL DEFAULT '{}',
    is_demo     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decompositions (
    id          TEXT PRIMARY KEY,
    source_id   TEXT,
    title       TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'processing',
    data        TEXT NOT NULL DEFAULT '{}',
    options     TEXT NOT NULL DEFAULT '{}',
    is_demo     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS versions (
    id                TEXT PRIMARY KEY,
    decomposition_id  TEXT NOT NULL,
    version           INTEGER NOT NULL,
    data              TEXT NOT NULL,
    note              TEXT NOT NULL DEFAULT '',
    created_at        TEXT NOT NULL,
    FOREIGN KEY(decomposition_id) REFERENCES decompositions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    stat_date       TEXT PRIMARY KEY,
    followers_total INTEGER NOT NULL DEFAULT 0,
    followers_add   INTEGER NOT NULL DEFAULT 0,
    followers_del   INTEGER NOT NULL DEFAULT 0,
    followers_net   INTEGER NOT NULL DEFAULT 0,
    play_total      INTEGER NOT NULL DEFAULT 0,
    like_total      INTEGER NOT NULL DEFAULT 0,
    comment_total   INTEGER NOT NULL DEFAULT 0,
    forward_total   INTEGER NOT NULL DEFAULT 0,
    fav_total       INTEGER NOT NULL DEFAULT 0,
    top_play        INTEGER NOT NULL DEFAULT 0,
    top_title       TEXT NOT NULL DEFAULT '',
    engagement_rate REAL NOT NULL DEFAULT 0,
    synced_at       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ok',
    raw             TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_decomp_created ON decompositions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_versions_decomp ON versions(decomposition_id, version DESC);

CREATE TABLE IF NOT EXISTS phone_links (
    id          TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    account     TEXT NOT NULL DEFAULT '',
    note        TEXT NOT NULL DEFAULT '',
    used        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id          TEXT PRIMARY KEY,
    platform    TEXT NOT NULL DEFAULT '视频号',
    name        TEXT NOT NULL DEFAULT '',
    username    TEXT NOT NULL DEFAULT '',
    avatar      TEXT NOT NULL DEFAULT '',
    bio         TEXT NOT NULL DEFAULT '',
    metrics     TEXT NOT NULL DEFAULT '{}',
    videos      TEXT NOT NULL DEFAULT '[]',
    analysis    TEXT NOT NULL DEFAULT '',
    filters     TEXT NOT NULL DEFAULT '{}',
    fetched_at  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "demo_mode": True,
    "asr_model": "faster-whisper-large-v3",
    "llm_model": "Qwen3-14B（本地）",
    "writing_model": "DeepSeek API",
    "data_dir": str(config.DATA_DIR),
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    config.ensure_dirs()
    with db() as conn:
        conn.executescript(SCHEMA)
        # 老库补列：options 记录本条拆解的用户选项（是否做分镜等）
        acols = {row["name"] for row in conn.execute("PRAGMA table_info(accounts)")}
        if "filters" not in acols:
            conn.execute("ALTER TABLE accounts ADD COLUMN filters TEXT NOT NULL DEFAULT '{}'")
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(decompositions)")}
        if "options" not in cols:
            conn.execute(
                "ALTER TABLE decompositions ADD COLUMN options TEXT NOT NULL DEFAULT '{}'"
            )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )


def get_setting(key: str, default: Any = None) -> Any:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return default


def set_setting(key: str, value: Any) -> None:
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def log_event(kind: str, payload: dict | None = None) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO events(type, payload, created_at) VALUES(?, ?, ?)",
            (kind, json.dumps(payload or {}, ensure_ascii=False), now_iso()),
        )


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


METRIC_FIELDS = (
    "stat_date", "followers_total", "followers_add", "followers_del", "followers_net",
    "play_total", "like_total", "comment_total", "forward_total", "fav_total",
    "top_play", "top_title", "engagement_rate", "synced_at", "status", "raw",
)


def save_metric(metric: dict) -> None:
    int_fields = (
        "followers_total", "followers_add", "followers_del", "followers_net",
        "play_total", "like_total", "comment_total", "forward_total", "fav_total",
        "top_play",
    )
    row = {k: int(metric.get(k) or 0) for k in int_fields}
    row.update({
        "stat_date": metric["stat_date"],
        "engagement_rate": float(metric.get("engagement_rate") or 0),
        "top_title": str(metric.get("top_title") or ""),
        "synced_at": str(metric.get("synced_at") or now_iso()),
        "status": str(metric.get("status") or "ok"),
        "raw": str(metric.get("raw") or "{}"),
    })
    with db() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO daily_metrics({', '.join(METRIC_FIELDS)}) "
            f"VALUES({', '.join('?' * len(METRIC_FIELDS))})",
            [row.get(k) for k in METRIC_FIELDS],
        )


def get_metric(stat_date: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM daily_metrics WHERE stat_date=?", (stat_date,)).fetchone()
    return dict(row) if row else None


def latest_metric() -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM daily_metrics ORDER BY stat_date DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def list_metrics(limit: int = 30) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_metrics ORDER BY stat_date DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def reset_stale_transcribing() -> None:
    """服务重启时，把没跑完的转写标记为失败，避免一直显示"转写中"。"""
    with db() as conn:
        rows = conn.execute(
            "SELECT id, meta FROM sources WHERE status='transcribing'"
        ).fetchall()
        for row in rows:
            try:
                meta = json.loads(row["meta"] or "{}")
            except Exception:
                meta = {}
            meta["error"] = "服务重启，转写中断，请重新点「开始转写」"
            conn.execute(
                "UPDATE sources SET status='transcribe_failed', meta=? WHERE id=?",
                (json.dumps(meta, ensure_ascii=False), row["id"]),
            )


def reset_stale_decompositions() -> None:
    """服务重启后，把卡住的拆解标成失败，避免永远停在「取链接中 / 拆解中」。

    定时器线程随进程消失，重启后这些任务不会再有人推进；标失败并写清原因，
    用户可以直接点「重新拆解」，不会留下僵尸记录。
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT id, status, data FROM decompositions WHERE status IN ('processing','preparing')"
        ).fetchall()
        for row in rows:
            try:
                data = json.loads(row["data"] or "{}")
            except Exception:
                data = {}
            msg = ("服务重启，取链接中断，请重新点「开始拆解」"
                   if row["status"] == "preparing"
                   else "服务重启，拆解中断，请点「重新拆解」")
            data["error"] = msg
            conn.execute(
                "UPDATE decompositions SET status='failed', data=?, updated_at=? WHERE id=?",
                (json.dumps(data, ensure_ascii=False), now_iso(), row["id"]),
            )


def get_source(source_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
    return dict(row) if row else None


def set_source_status(source_id: str, status: str, meta: dict | None = None) -> None:
    with db() as conn:
        if meta is None:
            conn.execute("UPDATE sources SET status=? WHERE id=?", (status, source_id))
        else:
            conn.execute(
                "UPDATE sources SET status=?, meta=? WHERE id=?",
                (status, json.dumps(meta, ensure_ascii=False), source_id),
            )


def save_account(data: dict, existing_id: str = "") -> str:
    """新建或覆盖一个对标账号；返回 id。"""
    account_id = existing_id or new_id("acc")
    now = now_iso()
    with db() as conn:
        row = conn.execute("SELECT id, created_at FROM accounts WHERE id=?", (account_id,)).fetchone()
        if row:
            conn.execute(
                """UPDATE accounts SET platform=?, name=?, username=?, avatar=?, bio=?,
                       metrics=?, videos=?, analysis=?, filters=?, fetched_at=?, updated_at=? WHERE id=?""",
                (data.get("platform", "视频号"), data.get("name", ""), data.get("username", ""),
                 data.get("avatar", ""), data.get("bio", ""),
                 json.dumps(data.get("metrics") or {}, ensure_ascii=False),
                 json.dumps(data.get("videos") or [], ensure_ascii=False),
                 data.get("analysis", ""),
                 json.dumps(data.get("filters") or {}, ensure_ascii=False),
                 data.get("fetched_at", ""), now, account_id),
            )
        else:
            conn.execute(
                """INSERT INTO accounts(id, platform, name, username, avatar, bio, metrics,
                       videos, analysis, filters, fetched_at, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id, data.get("platform", "视频号"), data.get("name", ""),
                 data.get("username", ""), data.get("avatar", ""), data.get("bio", ""),
                 json.dumps(data.get("metrics") or {}, ensure_ascii=False),
                 json.dumps(data.get("videos") or [], ensure_ascii=False),
                 data.get("analysis", ""),
                 json.dumps(data.get("filters") or {}, ensure_ascii=False),
                 data.get("fetched_at", ""), now, now),
            )
    return account_id


def get_account(account_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    for key in ("metrics", "videos", "filters"):
        try:
            item[key] = json.loads(item.get(key) or ("[]" if key == "videos" else "{}"))
        except Exception:
            item[key] = [] if key == "videos" else {}
    return item


def list_accounts() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM accounts ORDER BY updated_at DESC").fetchall()
    items = []
    for row in rows:
        item = dict(row)
        try:
            item["videos"] = json.loads(item.get("videos") or "[]")
        except Exception:
            item["videos"] = []
        try:
            item["metrics"] = json.loads(item.get("metrics") or "{}")
        except Exception:
            item["metrics"] = {}
        try:
            item["filters"] = json.loads(item.get("filters") or "{}")
        except Exception:
            item["filters"] = {}
        item["video_count"] = len(item["videos"])
        item.pop("videos", None)
        items.append(item)
    return items


def delete_account(account_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))


def save_transcript(source_id: str, transcript: str, duration: float, meta: dict) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE sources SET status='transcribed', transcript=?, duration=?, meta=? WHERE id=?",
            (transcript, duration, json.dumps(meta, ensure_ascii=False), source_id),
        )


def _seed_decompositions() -> list[dict]:
    """演示数据：内容为虚构示例，页面上会明确标注。"""
    from .demo import build_demo

    samples = [
        ("为什么你越努力，反而越焦虑", "林间说", "视频号", 3),
        ("3 个动作，改善久坐后的圆肩驼背", "身体使用说明", "视频号", 1),
        ("月薪 5000，也能开始的存钱顺序", "小账本", "抖音", 6),
        ("孩子写作业拖拉，先别催", "慢养研究所", "小红书", 2),
        ("我用一张表，管住了每天的精力", "效率手记", "视频号", 4),
        ("为什么你学了很多，却用不上", "认知切片", "抖音", 8),
    ]
    items = []
    for title, author, platform, days_ago in samples:
        created = (datetime.now() - timedelta(days=days_ago, hours=3)).isoformat(timespec="seconds")
        data = build_demo(title, author, platform)
        items.append({"title": title, "author": author, "platform": platform,
                      "created_at": created, "data": data})
    return items


def seed_demo() -> None:
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM decompositions").fetchone()["c"]
        if count:
            return
        for item in _seed_decompositions():
            source_id = new_id("src")
            conn.execute(
                """INSERT INTO sources(id, title, platform, author, url, status,
                       transcript, meta, is_demo, created_at)
                   VALUES(?, ?, ?, ?, '', 'ready', ?, ?, 1, ?)""",
                (source_id, item["title"], item["platform"], item["author"],
                 item["data"].get("transcript", ""),
                 json.dumps({"demo": True}, ensure_ascii=False), item["created_at"]),
            )
            decomp_id = new_id("dec")
            conn.execute(
                """INSERT INTO decompositions(id, source_id, title, status, data,
                       is_demo, created_at, updated_at)
                   VALUES(?, ?, ?, 'done', ?, 1, ?, ?)""",
                (decomp_id, source_id, item["title"],
                 json.dumps(item["data"], ensure_ascii=False),
                 item["created_at"], item["created_at"]),
            )
            conn.execute(
                """INSERT INTO versions(id, decomposition_id, version, data, note, created_at)
                   VALUES(?, ?, 1, ?, '初始拆解', ?)""",
                (new_id("ver"), decomp_id,
                 json.dumps(item["data"], ensure_ascii=False), item["created_at"]),
            )
