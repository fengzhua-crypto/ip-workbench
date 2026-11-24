"""画面字幕（硬字幕）识别。

思路：视频里作者通常已经打好了字幕，那是原文，比语音识别准得多。
这里抽帧 → 找字幕带 → 逐帧 OCR（画面没变就跳过）→ 拼成时间轴。

运行在 tools/ocr 的独立环境里（rapidocr），主程序只负责抽帧和调度。
"""
from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
from pathlib import Path

import av

from . import config

OCR_DIR = config.ROOT_DIR / "tools" / "ocr"
OCR_PY = OCR_DIR / ".venv" / "Scripts" / "python.exe"
OCR_SCRIPT = OCR_DIR / "subtitle_batch.py"

TMP_DIR = config.DATA_DIR / "tmp"
MAX_FRAMES = 900          # 最多处理 15 分钟，防止超长视频把机器拖住


class SubtitleUnavailable(RuntimeError):
    pass


def enabled() -> bool:
    if os.environ.get("IPWB_SUBTITLE_OCR", "1") == "0":
        return False
    return (OCR_PY.exists() and OCR_SCRIPT.exists())


def _extract_frames(video_path: Path, out_dir: Path) -> int:
    """每秒抽一帧，返回帧数。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    container = av.open(str(video_path))
    try:
        stream = container.streams.video[0]
        next_t = 0.0
        idx = 0
        for frame in container.decode(stream):
            t = float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
            if t + 0.001 < next_t:
                continue
            next_t += 1.0
            idx += 1
            frame.to_image().save(out_dir / f"{idx:04d}.jpg", quality=80)
            if idx >= MAX_FRAMES:
                break
        return idx
    finally:
        container.close()


def _run_ocr(frame_dir: Path, out_json: Path) -> dict:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.run(
        [str(OCR_PY), str(OCR_SCRIPT), str(frame_dir), str(out_json)],
        capture_output=True, timeout=3600, creationflags=flags,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "ignore").strip()
        raise SubtitleUnavailable(detail[:300] or "画面字幕识别失败")
    return json.loads(out_json.read_text(encoding="utf-8") or "{}")


def _timeline(payload: dict) -> list[dict]:
    frames = payload.get("frames") or []
    if not frames:
        return []

    # 固定水印（免责声明之类）会在几乎所有帧里一字不差地出现，按频次剔掉
    counts: dict[str, int] = {}
    for frame in frames:
        for text in {ln.get("text") or "" for ln in frame.get("lines") or []}:
            if text:
                counts[text] = counts.get(text, 0) + 1
    threshold = max(3, int(len(frames) * 0.5))

    segments: list[dict] = []
    last = ""
    for frame in frames:
        texts = [(ln.get("text") or "").strip() for ln in frame.get("lines") or []]
        text = "".join(t for t in texts if t and counts.get(t, 0) < threshold).strip()
        if not text or text == last:
            continue
        # 字幕切换那一两帧容易把新旧两条都读出来，相似度高的合并成一条（留长的）
        if segments:
            prev = segments[-1]["text"]
            if difflib.SequenceMatcher(None, prev, text).ratio() > 0.75:
                if len(text) > len(prev):
                    segments[-1]["text"] = text
                last = text
                continue
        segments.append({"start": float(frame.get("t", 0)), "text": text})
        last = text
    end_of_video = float(frames[-1].get("t", 0)) + 1.0
    for i, seg in enumerate(segments):
        seg["end"] = segments[i + 1]["start"] if i + 1 < len(segments) else end_of_video
    return segments


def extract(video_path: Path, duration: float = 0) -> dict:
    """返回 {"ok", "coverage", "count", "band", "segments", "reason"}。"""
    if not enabled():
        return {"ok": False, "reason": "画面字幕识别环境未安装（tools\\ocr）"}
    work = TMP_DIR / f"sub_{os.getpid()}_{int(duration)}"
    try:
        count = _extract_frames(Path(video_path), work)
        if count < 3:
            return {"ok": False, "reason": "抽帧失败"}
        payload = _run_ocr(work, work / "out.json")
        if not payload.get("band"):
            return {"ok": False, "reason": "没有检测到画面字幕"}
        segments = _timeline(payload)
        if not segments:
            return {"ok": False, "reason": "没有识别到画面字幕"}
        total = float(segments[-1]["end"]) or float(duration) or 1.0
        covered = sum(max(0.0, s["end"] - s["start"]) for s in segments)
        return {
            "ok": True,
            "coverage": round(covered / total, 3),
            "count": len(segments),
            "band": payload.get("band"),
            "segments": segments,
        }
    except SubtitleUnavailable as exc:
        return {"ok": False, "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"画面字幕识别失败：{exc}"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
