"""画面字幕识别：抽帧目录 → 找出字幕带 → 逐帧识别（画面没变就跳过）。

由主程序调用（独立虚拟环境，避免依赖冲突）：
    python subtitle_batch.py <抽帧目录> <输出 json>

输出：
    {"band": [y1, y2], "frames": [{"t": 0.0, "lines": [{"text": "..."}]}]}
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

MIN_SCORE = 0.7
DIFF_SKIP = 1.2          # 灰度平均差小于这个值，认为画面没变，沿用上一帧文字
SAMPLE_FRAMES = 6


def _lines_of(engine, image) -> list[dict]:
    res, _ = engine(image)
    out = []
    h = image.height if hasattr(image, "height") else image.shape[0]
    for box, text, score in (res or []):
        if float(score) < MIN_SCORE:
            continue
        text = (text or "").strip()
        if not text:
            continue
        ys = [float(p[1]) for p in box]
        out.append({"y1": min(ys) / h, "y2": max(ys) / h, "text": text})
    return out


def _pick_band(samples: list[list[dict]]) -> tuple[float, float] | None:
    """找“内容会变”的那条水平带：把只有一两行文字的固定水印排除掉。

    返回的是这条带子的实际上下边界（只留一点点余量），不能放宽——
    放宽会把旁边固定的免责声明一起框进来。
    """
    bins: dict[int, list[dict]] = {}
    for lines in samples:
        for ln in lines:
            key = int(round((ln["y1"] + ln["y2"]) / 2 * 20))  # 0.05 一档
            bins.setdefault(key, []).append(ln)

    best_key = None
    best_unique = 0
    for key, lines in bins.items():
        uniq = len({ln["text"] for ln in lines})
        if uniq >= 2 and uniq > best_unique:
            best_unique = uniq
            best_key = key
    if best_key is None:
        return None

    rows = bins[best_key]
    top = min(ln["y1"] for ln in rows)
    bottom = max(ln["y2"] for ln in rows)
    return max(0.0, top - 0.010), min(1.0, bottom + 0.010)


def main() -> int:
    if len(sys.argv) < 3:
        sys.stderr.write("用法: subtitle_batch.py <抽帧目录> <输出json>\n")
        return 2
    frame_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    frames = sorted(frame_dir.glob("*.jpg"))
    if not frames:
        out_path.write_text(json.dumps({"band": None, "frames": []}), encoding="utf-8")
        return 0

    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"OCR 引擎不可用: {exc}\n")
        return 3

    engine = RapidOCR()

    # 第一遍：抽样几帧全图识别，定位字幕带
    step = max(1, len(frames) // SAMPLE_FRAMES)
    samples = [_lines_of(engine, Image.open(f).convert("RGB")) for f in frames[::step][:SAMPLE_FRAMES]]
    band = _pick_band(samples)
    if not band:
        out_path.write_text(json.dumps({"band": None, "frames": []}, ensure_ascii=False), encoding="utf-8")
        return 0

    # 第二遍：只裁字幕带；画面没变就沿用上一帧的文字
    result = []
    prev_gray = None
    prev_lines: list[dict] = []
    for idx, path in enumerate(frames):
        img = Image.open(path).convert("RGB")
        w, h = img.size
        crop = img.crop((0, int(h * band[0]), w, int(h * band[1])))
        gray = np.asarray(crop.convert("L").resize((160, 40)), dtype=np.float32)
        if prev_gray is not None and np.mean(np.abs(gray - prev_gray)) < DIFF_SKIP:
            lines = prev_lines
        else:
            lines = _lines_of(engine, crop)
            prev_lines = lines
        prev_gray = gray
        result.append({"t": round(idx * 1.0, 2), "lines": lines})

    out_path.write_text(
        json.dumps({"band": [round(band[0], 3), round(band[1], 3)], "frames": result},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
