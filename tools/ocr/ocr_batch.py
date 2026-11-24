"""图文笔记图片文字提取（独立环境运行）。

用法：
    python ocr_batch.py <图片1> <图片2> ...

输出：标准输出一行 JSON：
    [{"file": "...", "lines": [{"text": "...", "score": 0.99}, ...]}, ...]
失败信息写到标准错误，退出码非 0。
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    # 输出固定用 UTF-8，避免中文在 cp936 管道里被破坏
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    paths = sys.argv[1:]
    if not paths:
        print("[]")
        return 0
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"OCR 引擎不可用: {exc}\n")
        return 2

    engine = RapidOCR()
    result = []
    for path in paths:
        item = {"file": path, "lines": []}
        try:
            res, _ = engine(path)
            for box, text, score in (res or []):
                text = (text or "").strip()
                if not text:
                    continue
                ys = [float(pt[1]) for pt in box]
                xs = [float(pt[0]) for pt in box]
                item["lines"].append({
                    "text": text,
                    "score": round(float(score), 3),
                    "y": round(min(ys), 1),
                    "h": round(max(ys) - min(ys), 1),
                    "x": round(min(xs), 1),
                    "w": round(max(xs) - min(xs), 1),
                })
        except Exception as exc:  # noqa: BLE001
            item["error"] = str(exc)
        result.append(item)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
