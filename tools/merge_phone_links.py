"""把手机抓回的链接解析成作品数据，合并进账号作品列表。

不重新抓取：只调用本机链接解析，拿到标题、发布时间、互动数，然后并入 accounts.videos。
用法：python tools/merge_phone_links.py "玖妈懂敏宝"
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import db, link_parser  # noqa: E402


def main(account_name: str) -> None:
    with db.db() as conn:
        rows = conn.execute(
            "SELECT id, url FROM phone_links ORDER BY created_at ASC"
        ).fetchall()
    print(f"手机链接 {len(rows)} 条", flush=True)

    videos = {}
    for row in rows:
        try:
            info = link_parser.parse(row["url"])
        except Exception as exc:  # noqa: BLE001
            print("解析失败", row["url"][-12:], str(exc)[:60], flush=True)
            continue
        stats = info.get("stats") or {}
        created = int(stats.get("createtime") or 0)
        published = dt.datetime.fromtimestamp(created).isoformat(timespec="seconds") if created else ""
        title = (info.get("title") or "").strip()
        key = row["url"][-10:]
        videos[key] = {
            "id": key,
            "text": title,
            "published_at": published,
            "likes": int(stats.get("like") or 0),
            "comments": int(stats.get("comment") or 0),
            "shares": int(stats.get("forward") or 0),
            "favorites": int(stats.get("fav") or 0),
            "duration": 0,
            "link": row["url"],
            "source": "phone",
        }
        print(f"{published[:10]} 转发{stats.get('forward')} {title[:30]}", flush=True)
        time.sleep(0.3)

    account = next((a for a in db.list_accounts() if a["name"] == account_name), None)
    if not account:
        raise SystemExit("账号不存在")
    full = db.get_account(account["id"])
    merged = {v.get("link") or v.get("id"): v for v in full.get("videos") or []}
    for key, video in videos.items():
        merged[key] = video
    ordered = sorted(merged.values(), key=lambda v: v.get("published_at") or "", reverse=True)
    full["videos"] = ordered
    full["fetched_at"] = db.now_iso()
    db.save_account(full, account["id"])
    print(f"合并完成：作品 {len(ordered)} 条", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "玖妈懂敏宝")
