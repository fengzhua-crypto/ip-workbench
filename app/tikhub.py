"""TikHub 数据接口适配：只用于视频号账号级对标（公开主页资料与作品列表）。

- Key 只存本机 data\\app.db，页面不回显。
- 只有账号 ID / username 会发出去，本机素材、字幕、稿子都不外发。
- 按调用计费（视频号端点约 $0.01/次），每次调用都写 events 日志，便于核对花费。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from . import config, db

BASE = "https://api.tikhub.io"
# Cloudflare 会拦非浏览器 UA，这里用常见浏览器标识
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class TikHubError(RuntimeError):
    """接口未配置、Key 无效、额度不足或网络失败。"""


def api_key() -> str:
    return str(db.get_setting("tikhub_api_key", "") or "").strip()


def configured() -> bool:
    return bool(api_key())


def _post(path: str, payload: dict, timeout: int = 45) -> dict:
    key = api_key()
    if not key:
        raise TikHubError("还没有配置 TikHub API Key，请到「设置 → 数据接口」填写")
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": UA,
            "Origin": "https://tikhub.io",
            "Referer": "https://tikhub.io/",
        },
    )
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
            message = ((json.loads(detail).get("detail") or {}).get("message_zh")
                       or (json.loads(detail).get("detail") or {}).get("message") or "")
        except Exception:  # noqa: BLE001
            message = detail[:200]
        if exc.code == 402:
            raise TikHubError("额度不足：" + (message or "该接口需要付费余额，不接受免费额度")) from exc
        if exc.code in (401, 403):
            raise TikHubError("Key 无效或没有该接口权限（HTTP %s）" % exc.code) from exc
        raise TikHubError(f"接口返回 HTTP {exc.code}：{message or detail[:200]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TikHubError("连不上 TikHub，请检查网络或代理") from exc
    try:
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise TikHubError("接口返回的不是 JSON") from exc
    # 所有计费调用统一在这里记账：本地 events 表就是花钱流水，一次都不能漏
    payload_keys = {k: v for k, v in (payload or {}).items() if k != "raw"}
    db.log_event("tikhub.call", {"path": path, "params": payload_keys, "est_usd": 0.01})
    return data


def _get(path: str, timeout: int = 20) -> dict:
    key = api_key()
    if not key:
        raise TikHubError("还没有配置 TikHub API Key")
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": UA,
                 "Origin": "https://tikhub.io", "Referer": "https://tikhub.io/"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        raise TikHubError(f"查询账号失败：{exc}") from exc


def account() -> dict:
    """账号余额（免费额度 / 付费余额），用于在设置页显示。"""
    data = _get("/api/v1/tikhub/user/get_user_info")
    user = (data.get("user_data") or {})
    return {
        "balance": user.get("balance", 0),
        "free_credit": user.get("free_credit", 0),
        "email_verified": user.get("email_verified", False),
        "key_name": (data.get("api_key_data") or {}).get("api_key_name", ""),
    }


def channel_to_username(channel_id: str) -> dict:
    """视频号 ID（sph 开头）→ 内部 username（v2_...@finder）。"""
    result = _post("/api/v1/wechat_channels/v2/fetch_channel_id_to_username",
                   {"channel_id": channel_id.strip(), "raw": True})
    return result


def user_profile(username: str) -> dict:
    result = _post("/api/v1/wechat_channels/v2/fetch_user_profile",
                   {"username": username, "raw": True})
    return result


def user_videos(username: str, last_buffer: str = "") -> dict:
    result = _post("/api/v1/wechat_channels/v2/fetch_user_videos",
                   {"username": username, "last_buffer": last_buffer or "", "raw": True})
    return result


def video_share_url(object_id: str) -> str:
    """作品 object_id → 分享短链（weixin.qq.com/sph/...）。$0.01/次，按需调用。"""
    result = _post("/api/v1/wechat_channels/v2/fetch_video_share_url",
                   {"object_id": str(object_id), "raw": False})
    data = result.get("data") if isinstance(result, dict) else None
    url = (data or {}).get("share_url") or ""
    if not url:
        raise TikHubError("接口没返回分享链接")
    return url


def probe(channel_id: str) -> dict:
    """三步探针：短号转 username → 主页资料 → 第一页作品。结果写 data\\exports 供核对。"""
    out = {"channel_id": channel_id}
    out["username_raw"] = channel_to_username(channel_id)
    username = _find_username(out["username_raw"])
    out["username"] = username
    if username:
        out["profile_raw"] = user_profile(username)
        out["videos_raw"] = user_videos(username)
    path = config.EXPORT_DIR / "tikhub_probe.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["saved_to"] = str(path)
    return out


def _find_username(payload) -> str:
    """在返回结构里找 v2_...@finder（接口字段名可能调整，做宽松查找）。"""
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
