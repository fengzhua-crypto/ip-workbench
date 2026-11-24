"""手机界面识别：先看屏幕，再决定点哪里（不写死坐标）。

- 文字类按钮：OCR 认出文字和位置，点文字中心；
- 找不到时退回按比例坐标（图标类按钮，如分享、返回）。
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

import cv2

# ADB 工具位置：优先读环境变量 ADB_PATH，换机器时设置它即可，不用改代码
ADB = Path(os.environ.get("ADB_PATH") or r"F:\Tools\platform-tools\adb.exe")
TMP = Path.home() / "AppData" / "Local" / "Temp"


class UIFail(RuntimeError):
    pass


def adb(device: str, *args: str, timeout: int = 30) -> str:
    cmd = [str(ADB), "-s", device, *args]
    out = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if out.returncode != 0:
        raise UIFail(out.stderr.decode("utf-8", "replace")[:200] or "adb 失败")
    return out.stdout.decode("utf-8", "replace")


def screen_size(device: str) -> tuple[int, int]:
    text = adb(device, "shell", "wm", "size")
    match = re.search(r"(\d+)x(\d+)", text)
    if not match:
        raise UIFail("读不到屏幕分辨率")
    return int(match.group(1)), int(match.group(2))


def grab(device: str) -> Path:
    path = TMP / "phone_ui.png"
    with path.open("wb") as fh:
        subprocess.run([str(ADB), "-s", device, "exec-out", "screencap", "-p"],
                       stdout=fh, timeout=30, check=False)
    return path


def read(device: str) -> tuple[list[dict], int, int]:
    """返回当前屏幕的文字块（含中心坐标）和屏幕尺寸。"""
    from rapidocr_onnxruntime import RapidOCR

    path = grab(device)
    img = cv2.imread(str(path))
    if img is None:
        raise UIFail("截图读取失败")
    height, width = img.shape[:2]
    result, _ = RapidOCR()(str(path))
    items = []
    for box, text, score in (result or []):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({
            "text": text,
            "cx": int(sum(xs) / 4),
            "cy": int(sum(ys) / 4),
            "x1": int(min(xs)), "y1": int(min(ys)),
            "x2": int(max(xs)), "y2": int(max(ys)),
            "score": float(score),
        })
    return items, width, height


def norm(text: str) -> str:
    return "".join(ch for ch in str(text) if ch.isalnum())


def find(items: list[dict], keyword: str, contains: bool = True) -> list[dict]:
    target = norm(keyword)
    hits = []
    for item in items:
        value = norm(item["text"])
        if (target and target in value) if contains else (value == target):
            hits.append(item)
    return hits


def tap_text(device: str, keyword: str, index: int = 0, wait: float = 1.0,
             contains: bool = True) -> dict:
    items, _, _ = read(device)
    hits = find(items, keyword, contains=contains)
    if len(hits) <= index:
        raise UIFail(f"屏幕上找不到「{keyword}」")
    item = hits[index]
    adb(device, "shell", "input", "tap", str(item["cx"]), str(item["cy"]))
    time.sleep(wait)
    return item


def tap_ratio(device: str, rx: float, ry: float, wait: float = 1.0) -> None:
    width, height = screen_size(device)
    adb(device, "shell", "input", "tap", str(int(width * rx)), str(int(height * ry)))
    time.sleep(wait)


def swipe_ratio(device: str, x1: float, y1: float, x2: float, y2: float,
                ms: int = 350, wait: float = 0.8) -> None:
    width, height = screen_size(device)
    adb(device, "shell", "input", "swipe",
        str(int(width * x1)), str(int(height * y1)),
        str(int(width * x2)), str(int(height * y2)), str(ms))
    time.sleep(wait)


def find_link(items: list[dict]) -> str:
    for item in items:
        match = re.search(r"https?://weixin\.qq\.com/sph/[A-Za-z0-9_-]+", item["text"])
        if match:
            return match.group(0)
    return ""
