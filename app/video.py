"""视频画面分析：真实切镜检测 + 关键帧。

- 本地做画面差分，不解码音频、不做 OCR，CPU 占用低。
- 关键帧保存在 data\\shots\\<source_id>\\，属于派生数据，可随时重新生成。
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from . import config, db

SHOT_DIR = config.DATA_DIR / "shots"
SAMPLE_FPS = 3.0
MIN_SHOT_SECONDS = 0.8
MIN_DIFF = 0.18


def _small_gray(frame) -> "object":
    import numpy as np

    img = frame.to_ndarray(format="gray")
    height, width = img.shape
    step_y = max(1, height // 90)
    step_x = max(1, width // 160)
    return img[::step_y, ::step_x].astype(np.float32)


def detect_shots(video_path: str, source_id: str, duration: float = 0) -> dict:
    """返回 {shots: [...], metrics: {...}}；没有视频轨时返回空。"""
    import av
    import numpy as np

    container = av.open(str(video_path))
    try:
        try:
            stream = next(s for s in container.streams if s.type == "video")
        except StopIteration:
            return {"shots": [], "metrics": {}}
        fps = float(stream.average_rate or 25)
        step = max(1, int(round(fps / SAMPLE_FPS)))

        times: list[float] = []
        diffs: list[float] = []
        prev = None
        for index, frame in enumerate(container.decode(stream)):
            if index % step:
                continue
            small = _small_gray(frame)
            if prev is not None:
                times.append(float(frame.time or 0))
                diffs.append(float(np.mean(np.abs(small - prev))))
            prev = small
    finally:
        container.close()

    if not diffs:
        return {"shots": [], "metrics": {}}

    median = statistics.median(diffs)
    mad = statistics.median([abs(d - median) for d in diffs]) or 0.01
    threshold = max(MIN_DIFF, median + 6 * mad)
    cuts = [0.0]
    for t, d in zip(times, diffs):
        if d >= threshold and t - cuts[-1] >= MIN_SHOT_SECONDS:
            cuts.append(round(t, 2))

    total = duration or (times[-1] + 1 / SAMPLE_FPS if times else 0)
    cut_dir = SHOT_DIR / source_id
    cut_dir.mkdir(parents=True, exist_ok=True)
    for old in cut_dir.glob("*.jpg"):
        old.unlink()

    shots = []
    for i, start in enumerate(cuts):
        end = cuts[i + 1] if i + 1 < len(cuts) else round(total, 2)
        if end - start < 0.3:
            continue
        shots.append({
            "index": len(shots) + 1,
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "keyframe": "",
        })

    # 第二次解码，保存每个镜头的关键帧
    if shots:
        container = av.open(str(video_path))
        try:
            stream = next(s for s in container.streams if s.type == "video")
            idx = 0
            for frame in container.decode(stream):
                t = float(frame.time or 0)
                while idx < len(shots) and t >= shots[idx]["start"] - 0.01:
                    image = frame.to_image()
                    if image.width > 480:
                        ratio = 480 / image.width
                        image = image.resize((480, max(1, int(image.height * ratio))))
                    name = f"shot_{shots[idx]['index']:03d}.jpg"
                    image.save(cut_dir / name, format="JPEG", quality=82)
                    shots[idx]["keyframe"] = name
                    idx += 1
                if idx >= len(shots):
                    break
        finally:
            container.close()

    durations = [s["duration"] for s in shots if s["duration"] > 0]
    metrics = {
        "shots": len(shots),
        "avg_shot": round(sum(durations) / len(durations), 2) if durations else 0,
        "cuts_per_minute": round(len(shots) / (total / 60), 1) if total else 0,
        "threshold": round(threshold, 4),
    }
    return {"shots": shots, "metrics": metrics}
