"""本地语音转写（faster-whisper）。

- 模型放在项目内的 data\\models 下，不写 C 盘用户目录。
- 默认模型 small（约 460MB），第一次转写时自动下载。
- 优先尝试显卡加速；显卡驱动/运行库不满足时自动退回 CPU（int8）。
- 转写文本写入 sources.transcript（原始素材，不覆盖），状态写入 sources.status。
"""
from __future__ import annotations

import json
import os
import queue
import site
import threading
import time
from pathlib import Path

from . import config, db, ocr, subtitles, video

MODEL_DIR = config.DATA_DIR / "models"
DEFAULT_MODEL = os.environ.get("IPWB_WHISPER_MODEL", "medium")
USE_VAD = os.environ.get("IPWB_ASR_VAD", "1") != "0"
SAMPLE_RATE = 16000

# 国内直连 huggingface.co 基本连不上（报 WinError 10061），首次下载模型会直接失败。
# 这里默认切到国内镜像；要换回官方或别的镜像，设环境变量 IPWB_HF_ENDPOINT 即可。
# 必须在 import faster_whisper / huggingface_hub 之前设置，所以放在模块顶层。
HF_ENDPOINT = (os.environ.get("IPWB_HF_ENDPOINT") or "https://hf-mirror.com").strip()
if HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT

_q: "queue.Queue[str]" = queue.Queue()
_queued: set[str] = set()
_q_lock = threading.Lock()
_worker: threading.Thread | None = None
_current: str | None = None
_progress: dict[str, int] = {}

_model = None
_model_key = ""
_model_device = ""
_model_lock = threading.Lock()
_dll_handles: list = []


def model_name() -> str:
    name = db.get_setting("asr_model_name", DEFAULT_MODEL)
    return str(name or DEFAULT_MODEL).strip()


def _setup_cuda_paths() -> None:
    """把 pip 装的 CUDA 运行库目录加进搜索路径。

    ctranslate2 在 Windows 上从 PATH 加载 cublas / cudnn 等 DLL；
    没装显卡运行库时什么都不做，照样走 CPU。
    """
    dirs = []
    try:
        bases = site.getsitepackages()
    except Exception:
        bases = []
    for base in bases:
        nvidia = Path(base) / "nvidia"
        if nvidia.is_dir():
            dirs += [str(p) for p in nvidia.glob("*/bin") if p.is_dir()]
    if not dirs:
        return
    current = os.environ.get("PATH", "")
    missing = [d for d in dirs if d not in current]
    if missing:
        os.environ["PATH"] = os.pathsep.join(missing + [current])
    if hasattr(os, "add_dll_directory"):
        for d in dirs:
            try:
                _dll_handles.append(os.add_dll_directory(d))
            except OSError:
                pass


def _load_model():
    global _model, _model_key, _model_device
    name = model_name()
    with _model_lock:
        if _model is not None and _model_key == name:
            return _model

        _setup_cuda_paths()
        from faster_whisper import WhisperModel  # 体积大，用到时再导入

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        prefer = os.environ.get("IPWB_WHISPER_DEVICE", "auto").lower()
        attempts: list[tuple[str, str]] = []
        if prefer in ("auto", "cuda"):
            attempts += [("cuda", "float16"), ("cuda", "int8_float16")]
        attempts.append(("cpu", "int8"))

        errors = []
        for device, compute in attempts:
            try:
                _model = WhisperModel(
                    name, device=device, compute_type=compute,
                    download_root=str(MODEL_DIR),
                )
                _model_key = name
                _model_device = device
                return _model
            except Exception as exc:  # 显卡不可用时退回 CPU
                errors.append(f"{device}/{compute}: {exc}")
                _model = None
        raise RuntimeError(_model_error(errors))


def _model_error(errors: list[str]) -> str:
    """把底层的一长串英文异常，翻成能照着做的中文提示。"""
    joined = "；".join(errors)
    network = any(k in joined for k in (
        "ConnectError", "10061", "Connection", "timed out", "Timeout", "Temporary failure",
    ))
    if network:
        return (
            "语音模型下载失败：这台电脑连不上模型仓库。"
            f"当前使用的地址是 {HF_ENDPOINT or '默认'}。"
            "处理办法：① 换个网络再点一次转写；"
            "② 或者把另一台已下载好模型的电脑里的 data\\models 文件夹，整个复制到本机同一位置。"
        )
    return "模型加载失败：" + joined


def _mark_failed(source_id: str, message: str) -> None:
    row = db.get_source(source_id)
    if not row:
        return
    try:
        meta = json.loads(row["meta"] or "{}")
    except Exception:
        meta = {}
    meta["error"] = message
    db.set_source_status(source_id, "transcribe_failed", meta)
    db.log_event("asr.failed", {"source": source_id, "error": message})


def _load_audio(path: Path, sample_rate: int = SAMPLE_RATE):
    """用 PyAV 解码成 16kHz 单声道浮点数组。

    不走 faster-whisper 自带的解码（新版 PyAV 改了参数名），也不依赖系统 FFmpeg。
    """
    import av
    import numpy as np

    container = av.open(str(path))
    try:
        try:
            stream = next(s for s in container.streams if s.type == "audio")
        except StopIteration:
            raise RuntimeError("这个文件里没有音频轨，无法转写")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
        chunks: list = []

        def take(frames) -> None:
            if not isinstance(frames, list):
                frames = [frames]
            for frame in frames:
                chunks.append(frame.to_ndarray().reshape(-1))

        for frame in container.decode(stream):
            take(resampler.resample(frame))
        take(resampler.resample(None))
    finally:
        container.close()

    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32) / 32768.0


_SENT_END = "。！？!?；;…"


def _merge_ranges(ranges: list[tuple[float, float]], gap: float = 3.0) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in sorted(ranges):
        if merged and start - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


_PAUSE_SPLIT = "，,、"


def _build_paragraphs(words: list[dict]) -> list[dict]:
    """把词级时间戳重组成句子，再按停顿合并成自然段。"""
    sentences: list[dict] = []
    buf: list[dict] = []
    for i, word in enumerate(words):
        buf.append(word)
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt["start"] - word["end"]) if nxt else 0
        token = (word.get("word") or "").strip()
        current_text = "".join(w["word"] for w in buf)
        end_char = token[-1] if token else ""
        hit_end = end_char and end_char in _SENT_END
        hit_pause = end_char and end_char in _PAUSE_SPLIT and len(current_text) >= 40
        if hit_end or hit_pause or gap > 0.8 or len(current_text) >= 90 or nxt is None:
            text = " ".join(current_text.split())
            if text:
                sentences.append({
                    "start": round(buf[0]["start"], 2),
                    "end": round(buf[-1]["end"], 2),
                    "text": text,
                })
            buf = []

    paragraphs: list[dict] = []
    current: dict | None = None
    for sentence in sentences:
        if current is None:
            current = dict(sentence)
            continue
        gap = sentence["start"] - current["end"]
        # 段落别太长：超过 70 字就断开，句号收尾且已有 40 字也断开
        ended = current["text"][-1:] in _SENT_END
        if gap > 1.0 or len(current["text"]) >= 70 or (ended and len(current["text"]) >= 40):
            paragraphs.append(current)
            current = dict(sentence)
        else:
            current["text"] += sentence["text"]
            current["end"] = sentence["end"]
    if current:
        paragraphs.append(current)
    return paragraphs


def _paragraphs_from_segments(segs: list[dict]) -> list[dict]:
    """没有词级时间戳时，用段级时间戳合并成自然段（同样控制长度）。"""
    paragraphs: list[dict] = []
    current: dict | None = None
    for seg in segs:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if current is None:
            current = {"start": seg["start"], "end": seg["end"], "text": text}
            continue
        gap = float(seg["start"]) - float(current["end"])
        ended = current["text"][-1:] in _SENT_END
        if gap > 1.0 or len(current["text"]) >= 70 or (ended and len(current["text"]) >= 40):
            paragraphs.append(current)
            current = {"start": seg["start"], "end": seg["end"], "text": text}
        else:
            current["text"] += text
            current["end"] = seg["end"]
    if current:
        paragraphs.append(current)
    return paragraphs


def _transcribe(source_id: str) -> None:
    row = db.get_source(source_id)
    if not row:
        raise RuntimeError("素材不存在")
    path = Path(row.get("file_path") or "")
    if not path.is_file():
        raise RuntimeError("没有找到本地视频文件，暂时不能转写")

    audio = _load_audio(path)
    if not len(audio):
        raise RuntimeError("这个文件里没有可识别的音频")

    model = _load_model()
    started = time.time()
    segments, info = model.transcribe(
        audio,
        language=None,
        beam_size=5,
        vad_filter=USE_VAD,
        condition_on_previous_text=False,
        # 词级时间戳开着会漏字（实测同一条视频 208 字 vs 266 字，中段整句消失），
        # 段落与分镜用段级时间戳已经够用，所以保持关闭。
        word_timestamps=False,
        initial_prompt="以下是普通话口播视频的字幕，请输出简体中文，并加标点。",
    )

    duration = round(len(audio) / SAMPLE_RATE, 2)
    parts: list[str] = []
    segs: list[dict] = []
    words_all: list[dict] = []
    suspect_ranges: list[tuple[float, float]] = []
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        if getattr(seg, "avg_logprob", 0.0) < -0.8 and len(text) >= 6:
            suspect_ranges.append((float(seg.start), float(seg.end)))
        words = []
        for w in (seg.words or []):
            token = (w.word or "")
            if not token:
                continue
            words.append({
                "start": round(float(w.start), 2),
                "end": round(float(w.end), 2),
                "word": token,
            })
        segs.append({
            "start": round(float(seg.start), 2),
            "end": round(float(seg.end), 2),
            "text": text,
            "avg_logprob": round(float(getattr(seg, "avg_logprob", 0.0)), 3),
            "words": words,
        })
        words_all.extend(words)
        parts.append(text)
        if duration:
            _progress[source_id] = min(99, int(float(seg.end) / duration * 100))
    paragraphs = _build_paragraphs(words_all) if words_all else _paragraphs_from_segments(segs)

    # 画面字幕优先：视频里作者自己打的字幕，比听音识别准得多
    subtitle_info: dict = {}
    if path.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v") and subtitles.enabled():
        sub = subtitles.extract(Path(path), duration)
        subtitle_info = {
            "ok": bool(sub.get("ok")),
            "coverage": sub.get("coverage", 0),
            "count": sub.get("count", 0),
            "band": sub.get("band"),
            "reason": sub.get("reason", ""),
        }
        if sub.get("ok") and sub.get("coverage", 0) >= 0.6 and len(sub.get("segments") or []) >= 5:
            # 用字幕时间轴替换转写结果，后面分段、分镜、拆解都按字幕走
            segs = [
                {"start": s["start"], "end": s["end"], "text": s["text"],
                 "avg_logprob": 0.0, "words": []}
                for s in sub["segments"]
            ]
            words_all = []
            paragraphs = _paragraphs_from_segments(segs)
            parts = [s["text"] for s in segs]
            subtitle_info["used"] = True
        else:
            subtitle_info["used"] = False

    raw_transcript = "\n".join(parts)
    suspect = _merge_ranges(suspect_ranges)
    ocr_lines: list[dict] = []
    ocr_error = ""
    ocr_on = ocr.ENABLED and bool(db.get_setting("ocr_enabled", False))
    if ocr_on:
        try:
            ocr_lines = ocr.extract(str(path), duration, focus=suspect or None)
        except ocr.OCRUnavailable as exc:
            ocr_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            ocr_error = f"OCR 失败：{exc}"

    try:
        source_options = (json.loads(row.get("meta") or "{}").get("options") or {})
    except Exception:
        source_options = {}
    want_storyboard = source_options.get("storyboard", True) is not False

    shots_data = {"shots": [], "metrics": {}}
    video_error = ""
    if not want_storyboard:
        video_error = "按设置跳过逐镜头分镜"
    elif path.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v"):
        try:
            shots_data = video.detect_shots(str(path), source_id, duration)
        except Exception as exc:  # noqa: BLE001
            video_error = str(exc)

    try:
        meta = json.loads(row.get("meta") or "{}")
    except Exception:
        meta = {}
    meta["asr"] = {
        "engine": "faster-whisper",
        "model": model_name(),
        "device": _model_device,
        "language": getattr(info, "language", "") or "",
        "language_probability": round(float(getattr(info, "language_probability", 0) or 0), 3),
        "duration": round(duration, 2),
        "elapsed": round(time.time() - started, 1),
        "segments": segs,
        "paragraphs": paragraphs,
        "raw_transcript": raw_transcript,
        "ocr": {
            "provider": "zhipu",
            "model": (db.get_setting("ocr_model", "") or "glm-4.6v-flash"),
            "lines": len(ocr_lines),
            "suspect_ranges": len(suspect),
            "error": ocr_error,
            "items": ocr_lines[:400],
        },
        "shots": shots_data.get("shots") or [],
        "video": {**(shots_data.get("metrics") or {}), "error": video_error},
        "subtitle": subtitle_info,
    }
    db.save_transcript(source_id, raw_transcript, duration, meta)
    db.log_event("asr.done", {
        "source": source_id,
        "seconds": round(time.time() - started, 1),
        "segments": len(segs),
        "device": _model_device,
    })


def _ensure_worker() -> None:
    global _worker
    if _worker and _worker.is_alive():
        return
    _worker = threading.Thread(target=_loop, name="asr-worker", daemon=True)
    _worker.start()


def _loop() -> None:
    global _current
    while True:
        source_id = _q.get()
        with _q_lock:
            _queued.discard(source_id)
            _current = source_id
        try:
            _transcribe(source_id)
        except Exception as exc:  # noqa: BLE001
            _mark_failed(source_id, str(exc))
        finally:
            _progress.pop(source_id, None)
            with _q_lock:
                _current = None
            _q.task_done()


def enqueue(source_id: str) -> dict:
    """把一条素材放进转写队列（后台执行，不阻塞页面）。"""
    row = db.get_source(source_id)
    if not row:
        return {"ok": False, "message": "素材不存在"}
    if not row.get("file_path") or not Path(row["file_path"]).is_file():
        return {"ok": False, "message": "这条素材没有本地视频文件，暂时不能转写"}
    with _q_lock:
        if source_id == _current or source_id in _queued:
            return {"ok": False, "message": "正在转写或已在排队"}
        _queued.add(source_id)
    db.set_source_status(source_id, "transcribing")
    _progress[source_id] = 0
    _ensure_worker()
    _q.put(source_id)
    return {"ok": True, "status": "transcribing"}


def progress(source_id: str) -> int | None:
    return _progress.get(source_id)


def status() -> dict:
    with _q_lock:
        current = _current
        waiting = len(_queued)
    name = model_name()
    return {
        "engine": "faster-whisper",
        "model": name,
        "device": _model_device,
        "loaded": _model is not None,
        "running": bool(current),
        "source_id": current or "",
        "queued": waiting,
    }
