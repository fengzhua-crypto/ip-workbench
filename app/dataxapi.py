"""DataXAPI 适配：视频号账号搜索 / 主页资料 / 作品列表。

- Key 只存本机 data\\app.db，页面不回显。
- 只发送账号昵称或内部 username，本机素材不外发。
- 每次调用带 X-Max-Price 上限，避免价格变动导致意外扣费。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from . import config, db

BASE = "https://api.dataxapi.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class DataXError(RuntimeError):
    """未配置、Key 无效、余额不足或网络失败。"""


def api_key() -> str:
    return str(db.get_setting("dataxapi_api_key", "") or "").strip()


def configured() -> bool:
    return bool(api_key())


def _get(path: str, params: dict, timeout: int = 40) -> dict:
    key = api_key()
    if not key:
        raise DataXError("还没有配置 DataXAPI Key，请到「设置 → 数据接口」填写")
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": UA,
        # 单次调用价格上限，超过就不执行
        "X-Max-Price": "0.10",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            detail = ""
        message = ""
        try:
            body = json.loads(detail)
            message = body.get("message_zh") or body.get("message") or ""
        except Exception:  # noqa: BLE001
            message = detail[:200]
        if exc.code == 401:
            raise DataXError("Key 无效或已过期") from exc
        if exc.code == 402:
            raise DataXError("额度不足：该接口需要付费余额（免费试用不包含或已用完）") from exc
        raise DataXError(f"接口返回 HTTP {exc.code}：{message or detail[:200]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DataXError("连不上 DataXAPI，请检查网络") from exc
    try:
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise DataXError("接口返回的不是 JSON") from exc


def search_user(name: str) -> dict:
    result = _get("/v1/wechat_channels/users/search", {"query": name, "view": "full"})
    db.log_event("dataxapi.call", {"api": "users.search"})
    return result


def user_get(user_id: str) -> dict:
    result = _get("/v1/wechat_channels/users/get", {"id": user_id, "view": "full"})
    db.log_event("dataxapi.call", {"api": "users.get"})
    return result


def user_videos(user_id: str, cursor: str = "") -> dict:
    params = {"id": user_id, "view": "full"}
    if cursor:
        params["cursor"] = cursor
    result = _get("/v1/wechat_channels/users/videos/list", params)
    db.log_event("dataxapi.call", {"api": "users.videos"})
    return result


def video_share_link(video_id: str) -> dict:
    result = _get("/v1/wechat_channels/videos/share_link/get",
                  {"id": video_id, "view": "full"})
    db.log_event("dataxapi.call", {"api": "videos.share_link"})
    return result


def normalize_video(item: dict) -> dict:
    metrics = item.get("metrics") or {}
    ext = item.get("ext") or {}
    return {
        "id": str(item.get("id") or ""),
        "text": (item.get("text") or "").strip(),
        "published_at": item.get("published_at") or "",
        "likes": int(metrics.get("likes") or 0),
        "comments": int(metrics.get("comments") or 0),
        "shares": int(metrics.get("shares") or 0),
        "favorites": int(metrics.get("favorites") or 0),
        "duration": ext.get("duration") or 0,
    }


def normalize_profile(item: dict) -> dict:
    metrics = item.get("metrics") or {}
    return {
        "id": str(item.get("id") or ""),
        "name": item.get("name") or "",
        "avatar": item.get("avatar_url") or "",
        "bio": item.get("bio") or "",
        "metrics": metrics,
    }


def _find_username(payload) -> str:
    hit = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and node.startswith("v2_") and node.endswith("@finder"):
            hit.append(node)

    walk(payload)
    return hit[0] if hit else ""


def probe(nickname: str) -> dict:
    """昵称 → 内部 username → 主页 → 第一页作品；原始返回存 data\\exports。"""
    out = {"nickname": nickname}
    out["search_raw"] = search_user(nickname)
    username = _find_username(out["search_raw"])
    out["username"] = username
    if username:
        out["profile_raw"] = user_get(username)
        out["videos_raw"] = user_videos(username)
    path = config.EXPORT_DIR / "dataxapi_probe.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["saved_to"] = str(path)
    return out
