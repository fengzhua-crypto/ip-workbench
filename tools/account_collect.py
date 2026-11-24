"""用 TikHub 采集视频号账号：主页资料 + 全量作品列表，边采边写库。

要点：
- **每翻 3 页就把已采到的作品写进 accounts.videos**，中途断了也不丢数据；
- 已经采过的账号，刷新时只翻到「遇到已知作品」为止，不重复全量扫；
- 分享链接不在这里取（$0.01/条），由「拆解这条」按需调用，避免为不拆的作品付费。

用法：
    python tools/account_collect.py "玖妈懂敏宝"          # 采集/刷新
    python tools/account_collect.py "玖妈懂敏宝" --full    # 强制全量重扫
    python tools/account_collect.py --import-json <路径>  # 把离线 JSON 导入账号
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import db  # noqa: E402

BASE = "https://api.tikhub.io"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SAVE_EVERY = 3          # 每翻几页落一次库
MAX_PAGES = 60          # 安全上限


class TikHub:
    def __init__(self) -> None:
        self.key = str(db.get_setting("tikhub_api_key", "") or "").strip()
        if not self.key:
            raise SystemExit("还没有配置 TikHub API Key（设置 → 数据接口）")

    def post(self, path: str, payload: dict, timeout: int = 90) -> dict:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={"Authorization": "Bearer " + self.key,
                     "Content-Type": "application/json",
                     "Accept": "application/json",
                     "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") != 200:
            raise RuntimeError(f'TikHub 返回 {data.get("code")}：{data.get("message_zh") or data.get("message")}')
        return data.get("data") or {}


def _iso(ts: int | None) -> str:
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds")


def normalize(v: dict) -> dict:
    """TikHub 作品 → 工作台作品结构。"""
    media = v.get("media") or {}
    return {
        "id": str(v.get("id") or ""),
        "text": (v.get("title") or v.get("description") or "").strip(),
        "published_at": _iso(v.get("create_time")),
        "likes": int(v.get("like_count") or 0),
        "comments": int(v.get("comment_count") or 0),
        "shares": int(v.get("forward_count") or 0),
        "favorites": int(v.get("fav_count") or 0),
        "duration": int(media.get("duration") or 0),
        "cover": (media.get("cover_url") or v.get("cover_img_url") or ""),
        "link": "",
        "source": "tikhub",
        "pinned": bool(v.get("pinned")),
    }


def mark_pinned(videos: list[dict], page1_order: list[str]) -> None:
    """TikHub 不返回置顶标记；置顶作品会在第一页打乱时间顺序排在最前面。

    规则：第一页去掉置顶后是严格按时间倒序的，所以找「最长的倒序后缀」，
    它前面的部分就是置顶。
    """
    if not page1_order:
        return
    by_id = {v["id"]: v for v in videos}
    dates = [(by_id.get(vid, {}).get("published_at") or "")[:10] for vid in page1_order]
    if not any(dates):
        return
    # 从末尾往前找倒序后缀的起点
    start = len(dates) - 1
    while start > 0:
        prev, cur = dates[start - 1], dates[start]
        if prev and cur and prev >= cur:
            start -= 1
        else:
            break
    for vid in page1_order[:start]:
        if vid in by_id:
            by_id[vid]["pinned"] = True


def dedupe(videos: list[dict]) -> list[dict]:
    """按「标题前 24 字 + 发布日期」去重；保留 tikhub 记录，但继承手机抓到的链接。"""
    seen: dict[tuple, dict] = {}
    for v in videos:
        key = ((v.get("text") or "")[:24], (v.get("published_at") or "")[:10])
        old = seen.get(key)
        if not old:
            seen[key] = v
            continue
        # 优先保留来源为 tikhub 的记录，链接则谁的都留
        keep, drop = (v, old) if v.get("source") == "tikhub" else (old, v)
        keep["link"] = keep.get("link") or drop.get("link") or ""
        keep["pinned"] = bool(keep.get("pinned")) or bool(drop.get("pinned"))
        seen[key] = keep
    return list(seen.values())


def collect(name: str, full: bool = False, save: bool = True) -> dict:
    api = TikHub()
    account = next((a for a in db.list_accounts() if a["name"] == name), None)
    existing: dict[str, dict] = {}
    if account:
        full_rec = db.get_account(account["id"]) or {}
        existing = {str(v.get("id")): v for v in (full_rec.get("videos") or []) if v.get("id")}
    username = (account or {}).get("username") or ""
    if not username:
        raise SystemExit(f"账号「{name}」还没有用户名，请先在页面添加账号")

    profile = api.post("/api/v1/wechat_channels/v2/fetch_user_profile",
                       {"username": username, "raw": False})
    print(f"主页：{profile.get('nickname')} · 作品数 {profile.get('feeds_count')}", flush=True)

    videos: dict[str, dict] = dict(existing)
    page1_order: list[str] = []
    last_buffer = ""
    pages = 0
    added = 0
    while pages < MAX_PAGES:
        payload = {"username": username, "last_buffer": last_buffer, "raw": False}
        data = api.post("/api/v1/wechat_channels/v2/fetch_user_videos", payload)
        items = data.get("videos") or []
        pages += 1
        new = 0
        for raw in items:
            vid = str(raw.get("id") or "")
            if not vid:
                continue
            if pages == 1:
                page1_order.append(vid)
            if vid not in videos:
                videos[vid] = normalize(raw)
                new += 1
            else:
                # 已有作品刷新互动数，但保留手机抓到的链接
                old = videos[vid]
                fresh = normalize(raw)
                fresh["link"] = old.get("link") or ""
                fresh["pinned"] = old.get("pinned") or fresh.get("pinned")
                videos[vid] = fresh
        added += new
        print(f"  第 {pages} 页：返回 {len(items)} 条，新增 {new} 条，累计 {len(videos)}",
              flush=True)
        if not items:
            break
        if not full and pages > 1 and new == 0:
            print("  已接上历史数据，停止翻页", flush=True)
            break
        last_buffer = data.get("last_buffer") or ""
        if not last_buffer:
            break
        if save and pages % SAVE_EVERY == 0:
            _persist(account, profile, videos, page1_order, name)
    _persist(account, profile, videos, page1_order, name)
    print(f"完成：共 {len(videos)} 条（本次新增 {added}），已写入账号作品列表", flush=True)
    return {"videos": len(videos), "added": added, "pages": pages}


def import_json(path: str, name: str, profile: dict | None = None) -> dict:
    """把离线 JSON 导入账号作品列表（不花接口钱）。

    注意：profile 传 None 时，必须保留库里原有的昵称/简介/指标，
    否则会像上次那样把真简介覆盖成空。
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    account = next((a for a in db.list_accounts() if a["name"] == name), None)
    if not account:
        raise SystemExit(f"账号「{name}」不存在")
    full_rec = db.get_account(account["id"]) or {}
    if profile is None:
        profile = {
            "nickname": full_rec.get("name") or name,
            "username": full_rec.get("username") or "",
            "head_url": full_rec.get("avatar") or "",
            "signature": full_rec.get("bio") or "",
            "feeds_count": (full_rec.get("metrics") or {}).get("posts"),
            "fans_count": (full_rec.get("metrics") or {}).get("fans"),
            "like_count": (full_rec.get("metrics") or {}).get("likes_total"),
            "forward_count": (full_rec.get("metrics") or {}).get("forward_total"),
            "region": (full_rec.get("metrics") or {}).get("region"),
        }
    videos = {str(v.get("id")): v for v in (full_rec.get("videos") or []) if v.get("id")}
    page1_order = [str(v.get("id")) for v in raw[:15]]
    added = 0
    for item in raw:
        vid = str(item.get("id") or "")
        if not vid:
            continue
        if vid in videos:
            videos[vid]["link"] = videos[vid].get("link") or ""
            fresh = normalize(item)
            fresh["link"] = videos[vid]["link"]
            videos[vid] = fresh
        else:
            videos[vid] = normalize(item)
            added += 1
    _persist(account, profile or {"nickname": name, "feeds_count": len(raw)}, videos, page1_order, name)
    print(f"导入完成：{len(videos)} 条（新增 {added}）", flush=True)
    return {"videos": len(videos), "added": added}


def _persist(account: dict | None, profile: dict, videos: dict, page1_order: list, name: str) -> None:
    ordered = list(videos.values())
    mark_pinned(ordered, page1_order)
    ordered = dedupe(ordered)
    # 置顶在前，其余按发布时间倒序
    ordered.sort(key=lambda v: (0 if v.get("pinned") else 1, -_ts(v.get("published_at"))))
    data = {
        "platform": "视频号",
        "name": profile.get("nickname") or (account or {}).get("name") or name,
        "username": profile.get("username") or (account or {}).get("username") or "",
        "avatar": profile.get("head_url") or (account or {}).get("avatar") or "",
        "bio": profile.get("signature") or "",
        "metrics": {
            "posts": profile.get("feeds_count"),
            "fans": profile.get("fans_count") or 0,
            "likes_total": profile.get("like_count") or 0,
            "forward_total": profile.get("forward_count") or 0,
            "region": profile.get("region") or "",
            "channels_id": (account or {}).get("metrics", {}).get("channels_id", ""),
        },
        "videos": ordered,
        # analysis 在库里就是 JSON 字符串，原样回写，不要二次编码
        "analysis": (account or {}).get("analysis") or "",
        "filters": (account or {}).get("filters") or {},
        "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    db.save_account(data, account["id"] if account else "")


def _ts(iso: str) -> int:
    try:
        return int(dt.datetime.fromisoformat((iso or "").replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="账号昵称")
    ap.add_argument("--full", action="store_true", help="强制全量重扫")
    ap.add_argument("--import-json", help="从 JSON 导入，不调用接口")
    args = ap.parse_args()
    if args.import_json:
        import_json(args.import_json, args.name or "玖妈懂敏宝")
    else:
        if not args.name:
            raise SystemExit("请给出账号昵称")
        collect(args.name, full=args.full)
