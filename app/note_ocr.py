"""图文笔记的图片文字提取。

OCR 引擎放在 tools\\ocr 的独立虚拟环境里跑（rapidocr-onnxruntime），
避免它的依赖和主程序的 onnxruntime / ctranslate2 锁版本冲突。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import config

ROOT = config.ROOT_DIR
OCR_DIR = ROOT / "tools" / "ocr"
OCR_PY = OCR_DIR / ".venv" / "Scripts" / "python.exe"
OCR_SCRIPT = OCR_DIR / "ocr_batch.py"


class OcrUnavailable(RuntimeError):
    """OCR 环境缺失或运行失败。"""


def available() -> bool:
    return OCR_PY.exists() and OCR_SCRIPT.exists()


def run(paths: list[Path], timeout: int = 900) -> list[dict]:
    """批量识别，返回 [{"file": ..., "lines": [{"text", "score"}], ...}]。"""
    paths = [Path(p) for p in paths]
    if not paths:
        return []
    if not available():
        raise OcrUnavailable("图片文字识别环境未安装（tools\\ocr\\.venv），请重新运行 install.bat")

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    proc = subprocess.run(
        [str(OCR_PY), str(OCR_SCRIPT), *[str(p) for p in paths]],
        capture_output=True, timeout=timeout, creationflags=flags,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "ignore").strip()
        raise OcrUnavailable(detail[:300] or "图片文字识别失败")
    raw = (proc.stdout or b"").decode("utf-8", "ignore").strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OcrUnavailable(f"OCR 返回格式异常：{exc}") from exc
