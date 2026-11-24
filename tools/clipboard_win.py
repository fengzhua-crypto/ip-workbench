"""读取 Windows 剪贴板（配合 scrcpy 的剪贴板同步使用）。"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import time

CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def get_text() -> str:
    for _ in range(20):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.1)
    else:
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
