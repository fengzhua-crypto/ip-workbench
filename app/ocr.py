"""云端字幕 OCR：抽帧裁出字幕区域，调用视觉模型识别。

- 默认智谱 GLM-4.6V-Flash（免费，限速）；地址/模型/Key 都在设置页可改。
- 只上传"字幕区域"的图片，不上传整段视频。
- 识别结果与原始转写分开保存：原始留在 meta.asr.raw_transcript。
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import db

DEFAULT_BASE = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-4.6v-flash"
MAX_FRAMES = 80
REQUEST_GAP = 1.0
ENABLED = os.environ.get("IPWB_OCR", "1") != "0"

PROMPT = (
    "只提取图片中视频字幕区域的中文文字，忽略英文翻译、水印、台标、背景文字和界面文字。"
    "按字幕阅读顺序输出，不要解释、不要加引号；如果画面里没有字幕，输出空字符串。"
)

_CJK = re.compile(r"[一-鿿0-9，。！？、；：,.!?;:%\-—–~·《》“”‘’（）()]")
_lock = threading.Lock()


class OCRUnavailable(RuntimeError):
    """云端 OCR 不可用（没配 Key、限流、网络问题等）。"""


def config() -> dict:
    return {
        "base_url": str(db.get_setting("ocr_base_url", DEFAULT_BASE) or DEFAULT_BASE).rstrip("/"),
        "model": str(db.get_setting("ocr_model", DEFAULT_MODEL) or DEFAULT_MODEL).strip(),
        "api_key": str(db.get_setting("ocr_api_key", "") or "").strip(),
    }


def status(check: bool = False) -> dict:
    cfg = config()
    result = {
        "base_url": cfg["base_url"], "model": cfg["model"],
        "key_set": bool(cfg["api_key"]), "available": False, "error": "",
    }
    if not result["key_set"] or not check:
        return result
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(buf, format="JPEG")
        text = _call(cfg, base64.b64encode(buf.getvalue()).decode(), "回复：连接正常")
        result["available"] = bool(text)
        if not text:
            result["error"] = "接口返回为空"
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def _call(cfg: dict, image_b64: str, prompt: str = PROMPT) -> str:
    payload = {
        "model": cfg["model"],
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ],
        }],
        "temperature": 0.01,
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {cfg['api_key']}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if exc.code == 401:
            raise OCRUnavailable("OCR API Key 无效或已过期") from exc
        if exc.code == 429:
            raise OCRUnavailable("OCR 请求太频繁（限流），请稍后再试") from exc
        raise OCRUnavailable(f"OCR 接口返回 {exc.code}：{body[:160]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise OCRUnavailable("连不上 OCR 接口，请检查网络或地址") from exc
    message = (data.get("choices") or [{}])[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "").strip()


def _clean(text: str) -> str:
    text = "".join(ch for ch in (text or "") if _CJK.match(ch))
    return re.sub(r"\s+", "", text)


def _merge(lines: list[dict], start: float, end: float, text: str) -> None:
    if not text:
        return
    if lines:
        last = lines[-1]
        if text == last["text"] or text in last["text"]:
            last["end"] = round(end, 2)
            return
        if last["text"] in text:
            last["text"] = text
            last["end"] = round(end, 2)
            return
    lines.append({"start": round(start, 2), "end": round(end, 2), "text": text})


def _jpeg_base64(frame, crop_bottom: float = 0.35, max_width: int = 960) -> str:
    image = frame.to_image()
    width, height = image.size
    crop = image.crop((0, int(height * (1 - crop_bottom)), width, height))
    if crop.width > max_width:
        ratio = max_width / crop.width
        crop = crop.resize((max_width, max(1, int(crop.height * ratio))))
    buf = io.BytesIO()
    crop.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _sample_times(focus: list[tuple[float, float]] | None, duration: float) -> list[float]:
    """全片均匀抽帧；低置信片段额外加密。"""
    times: set[float] = set()
    if duration:
        interval = max(3.0, duration / MAX_FRAMES)
        t = 0.0
        while t < duration and len(times) < MAX_FRAMES:
            times.add(round(t, 2))
            t += interval
    for start, end in focus or []:
        t = start
        while t <= end and len(times) < MAX_FRAMES:
            times.add(round(t, 2))
            t += 2.0
    return sorted(times)[:MAX_FRAMES]


def extract(video_path: str, duration: float = 0,
            focus: list[tuple[float, float]] | None = None) -> list[dict]:
    """抽样识别画面字幕，返回 [{start,end,text}]。

    focus：只在这些时间段抽帧（通常是语音识别置信度低的片段）。
    """
    if not ENABLED:
        return []
    cfg = config()
    if not cfg["api_key"]:
        raise OCRUnavailable("还没有配置画面字幕 OCR 的 API Key")

    import av

    times = _sample_times(focus, duration)
    if not times:
        return []
    container = av.open(str(video_path))
    frames: list[tuple[float, str]] = []
    try:
        try:
            stream = next(s for s in container.streams if s.type == "video")
        except StopIteration:
            return []
        idx = 0
        for frame in container.decode(stream):
            t = float(frame.time or 0)
            while idx < len(times) and times[idx] <= t + 0.35:
                frames.append((times[idx], _jpeg_base64(frame)))
                idx += 1
            if idx >= len(times):
                break
    finally:
        container.close()

    results: list[tuple[float, str]] = []
    errors = []
    for t, image in frames:
        text = ""
        for attempt in range(5):
            try:
                text = _clean(_call(cfg, image))
                break
            except OCRUnavailable as exc:
                if "限流" in str(exc):
                    time.sleep(4 + attempt * 4)
                    continue
                errors.append(str(exc))
                break
        results.append((t, text))
        time.sleep(REQUEST_GAP)

    lines: list[dict] = []
    for t, text in results:
        _merge(lines, t, t, text)
    if not lines and errors:
        raise OCRUnavailable(errors[0])
    return lines
