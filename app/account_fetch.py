"""对标账号采集：昵称 → 内部 ID → 主页资料 → 作品列表，边采边写库。

数据来源：TikHub 视频号 V2 接口，按请求计费（每个请求约 $0.01，一次返回 15 条）。
- 昵称搜索 1 次
- 主页资料 1 次
- 作品列表每页 1 次（近一年约 4~5 页，全量最多 20 页）

拿不到的字段（平台不公开，统一返回 0 并在界面标注，绝不估算）：
粉丝数、播放量、涨粉数、完播率。
"""
from __future__ import annotations

import datetime as dt
import json

from . import db, tikhub

SAVE_EVERY = 3
# 翻页安全上限：只防失控，不是范围控制。范围由时间边界（cutoff）和「接上历史」控制。
# 之前设 40 页导致大账号（郑奶奶 3789 条）「近一年」只抓到 5.5 个月就被截断。
MAX_PAGES = 400
YEAR_DAYS = 365


def _iso(ts) -> str:
    if not ts:
        return ""
    try:
        return dt.datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds")
    except Exception:
        return ""


def _ts(iso: str) -> int:
    try:
        return int(dt.datetime.fromisoformat((iso or "").replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _strip(text: str) -> str:
    """去掉搜索结果的 <em class="highlight"> 标签。"""
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def search_account(nickname: str) -> dict:
    """昵称 → 账号。返回 username / 昵称 / 头像 / 认证 / 简介。"""
    result = tikhub._post("/api/v1/wechat_search/v2/fetch_search",
                          {"keyword": nickname, "business_type": "account", "raw": False})
    items = (result.get("data") or {}).get("items") or []
    if not items:
        raise LookupError("没搜到这个昵称的视频号，请核对一字不差")
    # 优先标题完全一致的
    exact = [i for i in items if _strip(i.get("title")) == nickname.strip()]
    chosen = (exact or items)[0]
    username = ((chosen.get("jumpInfo") or {}).get("userName")
                or (chosen.get("noticeParam") or {}).get("finderUsername") or "")
    if not username:
        raise LookupError("搜索返回里没有账号内部 ID")
    return {
        "username": username,
        "nickname": _strip(chosen.get("title")) or nickname,
        "avatar": chosen.get("thumbUrl") or "",
        "auth": _strip(chosen.get("authInfo")) or "",
        "bio_hint": _strip(chosen.get("desc")) or "",
    }


def fetch_profile(username: str) -> dict:
    result = tikhub._post("/api/v1/wechat_channels/v2/fetch_user_profile",
                          {"username": username, "raw": False})
    p = result.get("data") or {}
    return {
        "username": p.get("username") or username,
        "name": p.get("nickname") or "",
        "avatar": p.get("head_url") or "",
        "bio": p.get("signature") or "",
        "region": p.get("region") or "",
        "posts": p.get("feeds_count") or 0,
        "fans": p.get("fans_count") or 0,
        "likes_total": p.get("like_count") or 0,
        "forward_total": p.get("forward_count") or 0,
        "verify": p.get("verify_desc") or "",
        "linked": p.get("linked_accounts") or [],
        # 以下字段之前取到了却没展示，现在全部保留
        "live_hours": p.get("live_duration_hours") or 0,
        "collections": p.get("collection_count") or 0,
        "original_flag": p.get("original_flag") or 0,
        "friend_follow": p.get("friend_follow_count") or 0,
    }


def preview(nickname: str) -> dict:
    """只看基础信息：搜索 + 主页 + 第一页（用来估算更新频率）。

    总花费约 $0.03；第一页那 15 条会直接入库，后续采集不会重复付费。
    不做整段采集，先让使用者知道「这个号多大、抓哪个范围要多少钱」。
    """
    hit = search_account(nickname)
    username = hit["username"]
    profile = fetch_profile(username)

    page = tikhub._post("/api/v1/wechat_channels/v2/fetch_user_videos",
                        {"username": username, "last_buffer": "", "raw": False})
    data = page.get("data") or {}
    items = data.get("videos") or []
    vids = {str(v.get("id")): normalize_video(v) for v in items if v.get("id")}
    order = [str(v.get("id")) for v in items if v.get("id")]

    # 用第一页 15 条的时间跨度估算月更量
    stamps = sorted((v.get("create_time") or 0) for v in items if v.get("create_time"))
    per_month = 0.0
    if len(stamps) >= 2 and stamps[-1] > stamps[0]:
        span_days = (stamps[-1] - stamps[0]) / 86400
        if span_days >= 1:
            per_month = len(stamps) / span_days * 30

    existing = next((a for a in db.list_accounts() if a["username"] == username), None)
    account_id = _persist(db.get_account(existing["id"]) if existing else None,
                          profile, vids, order, nickname, username,
                          hit.get("auth") or "", "preview")

    posts = int(profile.get("posts") or 0)
    estimates = {}
    for key, days in RANGE_DAYS.items():
        if key == "all" or not days:
            est = posts
        elif per_month:
            est = min(posts, int(per_month * days / 30))
        else:
            est = 0
        pages = max(1, -(-est // 15)) if est else 0
        estimates[key] = {"label": MODE_LABEL[key], "items": est,
                          "pages": pages, "usd": round(pages * 0.01, 2)}

    return {
        "account_id": account_id,
        "username": username,
        "name": profile.get("name") or hit["nickname"],
        "avatar": profile.get("avatar") or hit.get("avatar") or "",
        "bio": profile.get("bio") or hit.get("bio_hint") or "",
        "verify": profile.get("verify") or hit.get("auth") or "",
        "region": profile.get("region") or "",
        "posts": posts,
        "live_hours": profile.get("live_hours") or 0,
        "collections": profile.get("collections") or 0,
        "original_flag": profile.get("original_flag") or 0,
        "linked": profile.get("linked") or [],
        "per_month": round(per_month, 1),
        "estimates": estimates,
        "sample_count": len(vids),
        "not_available": ["粉丝数", "播放量", "账号总点赞/转发"],
    }


def full_text(v: dict) -> str:
    """保留完整文案：title 是干净标题，description 里带话题标签。

    两者内容不同时都要留，不能只取 title 把话题标签丢掉。
    """
    title = (v.get("title") or "").strip()
    desc = (v.get("description") or "").strip()
    if not desc:
        return title
    if not title:
        return desc
    if title in desc:
        return desc          # description 已经包含标题，直接用
    if desc in title:
        return title
    return title + "\n" + desc


def normalize_video(v: dict) -> dict:
    media = v.get("media") or {}
    return {
        "id": str(v.get("id") or ""),
        "text": full_text(v),
        "published_at": _iso(v.get("create_time")),
        "likes": int(v.get("like_count") or 0),
        "comments": int(v.get("comment_count") or 0),
        "shares": int(v.get("forward_count") or 0),
        "favorites": int(v.get("fav_count") or 0),
        "duration": int(media.get("duration") or 0),
        "cover": media.get("cover_url") or v.get("cover_img_url") or "",
        "link": "",
        "source": "tikhub",
        "pinned": False,
    }


def mark_pinned(videos: list[dict], page1_order: list[str]) -> None:
    """置顶作品会在第一页打乱时间顺序排在最前面。

    第一页去掉置顶后是严格按时间倒序的，所以找「最长的倒序后缀」，
    它前面的部分就是置顶。
    """
    if not page1_order:
        return
    by_id = {v["id"]: v for v in videos}
    dates = [(by_id.get(vid, {}).get("published_at") or "")[:10] for vid in page1_order]
    if not any(dates):
        return
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


def title_key(text: str) -> str:
    """只用于判断「是不是同一条作品」，不改动保存的标题。

    取第一行（干净标题）去掉空白和标点后的前 12 个字；
    话题标签和正文不参与比对，避免同一条作品因为一边带标签、一边不带而漏判。
    """
    import re
    first_line = (text or "").split("\n")[0]
    clean = re.sub(r"#\S+", "", first_line)
    clean = re.sub(r"[\s\W_]+", "", clean)
    return clean[:12]


def dedupe(videos: list[dict]) -> list[dict]:
    """按「归一化标题 + 日期」去重；保留 tikhub 记录并继承手机抓到的链接。"""
    seen: dict[tuple, dict] = {}
    for v in videos:
        key = (title_key(v.get("text")), (v.get("published_at") or "")[:10])
        old = seen.get(key)
        if not old:
            seen[key] = v
            continue
        keep, drop = (v, old) if v.get("source") == "tikhub" else (old, v)
        keep["link"] = keep.get("link") or drop.get("link") or ""
        keep["pinned"] = bool(keep.get("pinned")) or bool(drop.get("pinned"))
        # 标题取长的那个（接口给的可能被截断）
        if len(drop.get("text") or "") > len(keep.get("text") or ""):
            keep["text"] = drop["text"]
        seen[key] = keep
    return list(seen.values())


# 采集范围 → 天数。默认近 3 个月。
RANGE_DAYS = {"m1": 30, "m3": 90, "m6": 180, "y1": 365, "all": 0}
DEFAULT_RANGE = "m3"
MODE_LABEL = {"m1": "近 1 个月", "m3": "近 3 个月", "m6": "近 6 个月",
              "y1": "近 1 年", "all": "全部历史"}


def range_days(mode: str) -> int:
    return RANGE_DAYS.get(str(mode or DEFAULT_RANGE), RANGE_DAYS[DEFAULT_RANGE])


def collect(nickname: str, mode: str = DEFAULT_RANGE, account_id: str = "") -> str:
    """采集并写库，返回账号 id。

    mode（采集范围）：
      m1=近1个月 m3=近3个月（默认） m6=近6个月 y1=近1年 all=全部历史
    每 SAVE_EVERY 页落一次库，中途断了已采到的数据不丢。
    """
    account = db.get_account(account_id) if account_id else None
    auth = ""
    if not account:
        hit = search_account(nickname)
        username = hit["username"]
        auth = hit.get("auth") or ""
        existing = next((a for a in db.list_accounts() if a["username"] == username), None)
        account = db.get_account(existing["id"]) if existing else None
        auth = auth or ((account or {}).get("metrics") or {}).get("verify", "")
    else:
        username = account.get("username") or search_account(nickname)["username"]
        auth = (account.get("metrics") or {}).get("verify", "")

    profile = fetch_profile(username)
    existing_videos = {str(v.get("id")): v for v in ((account or {}).get("videos") or []) if v.get("id")}
    videos: dict[str, dict] = dict(existing_videos)
    page1_order: list[str] = []
    last_buffer = ""
    pages = 0
    added = 0
    days = range_days(mode)
    cutoff = dt.datetime.now() - dt.timedelta(days=days) if days else None

    while pages < MAX_PAGES:
        data = tikhub._post("/api/v1/wechat_channels/v2/fetch_user_videos",
                            {"username": username, "last_buffer": last_buffer, "raw": False})
        payload = data.get("data") or {}
        items = payload.get("videos") or []
        pages += 1
        new = 0
        known = 0
        oldest = None
        for raw in items:
            vid = str(raw.get("id") or "")
            if not vid:
                continue
            if pages == 1:
                page1_order.append(vid)
            fresh = normalize_video(raw)
            created = raw.get("create_time") or 0
            if created:
                oldest = created if oldest is None else min(oldest, created)
            if vid in videos:
                fresh["link"] = videos[vid].get("link") or ""
                fresh["pinned"] = bool(videos[vid].get("pinned"))
                known += 1
            else:
                new += 1
            videos[vid] = fresh
        added += new
        if pages % SAVE_EVERY == 0 or not items:
            new_id = _persist(account, profile, videos, page1_order, nickname, username, auth, mode)
            if not account:
                account = {"id": new_id}   # 首次创建后固定 id，避免重复建账号
        if not items:
            break
        last_buffer = payload.get("last_buffer") or ""
        if not last_buffer:
            break
        if cutoff is not None:
            # 列表按时间倒序：翻到「大部分都是已有作品」说明已接上历史，不用再往下扫
            if known >= max(8, len(items) * 0.6):
                break
            # 第 1 页混着置顶作品（日期很老），不能拿它判断时间边界
            if pages >= 2 and oldest and cutoff and dt.datetime.fromtimestamp(oldest) < cutoff:
                break
    new_id = _persist(account, profile, videos, page1_order, nickname, username, auth, mode)
    if not account:
        account = {"id": new_id}
    return account["id"]


def _persist(account, profile: dict, videos: dict, page1_order: list,
             nickname: str, username: str, auth: str = "", mode: str = DEFAULT_RANGE) -> None:
    ordered = list(videos.values())
    mark_pinned(ordered, page1_order)
    mode_label = MODE_LABEL.get(str(mode), MODE_LABEL[DEFAULT_RANGE])
    ordered = dedupe(ordered)
    ordered.sort(key=lambda v: (0 if v.get("pinned") else 1, -_ts(v.get("published_at"))))
    data = {
        "platform": "视频号",
        "name": profile.get("name") or (account or {}).get("name") or nickname,
        "username": username,
        "avatar": profile.get("avatar") or (account or {}).get("avatar") or "",
        "bio": profile.get("bio") or (account or {}).get("bio") or "",
        "metrics": {
            "posts": profile.get("posts"),
            "fans": profile.get("fans") or 0,
            "likes_total": profile.get("likes_total") or 0,
            "forward_total": profile.get("forward_total") or 0,
            "region": profile.get("region") or "",
            # 认证信息：主页接口的 verify_desc 优先，没有就用搜索结果里的认证标签
            "verify": (profile.get("verify") or auth
                       or ((account or {}).get("metrics") or {}).get("verify", "")),
            "channels_id": ((account or {}).get("metrics") or {}).get("channels_id", ""),
            # 以下都是主页接口本来就返回、之前没用上的信息
            "live_hours": profile.get("live_hours") or ((account or {}).get("metrics") or {}).get("live_hours", 0),
            "collections": profile.get("collections") or ((account or {}).get("metrics") or {}).get("collections", 0),
            "original_flag": profile.get("original_flag") or 0,
            "linked": profile.get("linked") or ((account or {}).get("metrics") or {}).get("linked", []),
            "range": mode_label,
        },
        "videos": ordered,
        "analysis": (account or {}).get("analysis") or "",
        "filters": (account or {}).get("filters") or {},
        "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    new_id = db.save_account(data, account["id"] if account else "")
    if not account:
        # 首次创建：把 id 回填给调用方后续落库使用
        account = {"id": new_id}
    return new_id
