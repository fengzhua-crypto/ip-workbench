"""PC 端界面工具：找窗口、原生截图、点击、滚轮、中英文输入。

只用 Python 标准库 ctypes + 本机已有 PIL/numpy，不依赖 pywin32、不装新东西。
截图优先 PrintWindow（窗口被遮挡也能截），失败退回 BitBlt。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as w
import time
from pathlib import Path

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

SW_RESTORE = 9
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000

EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"


def set_dpi_aware() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


set_dpi_aware()


def list_windows(keyword: str = "", pid: int = 0) -> list[dict]:
    """列出顶层窗口；keyword 匹配标题，pid 精确匹配进程。"""
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    out: list[dict] = []

    def cb(hwnd, _lparam):
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value
        own = w.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(own))
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        rect = w.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if pid and own.value != pid:
            return True
        if keyword and keyword not in title:
            return True
        out.append({
            "hwnd": hwnd, "pid": own.value, "title": title, "cls": cls.value,
            "visible": bool(user32.IsWindowVisible(hwnd)),
            "w": rect.right - rect.left, "h": rect.bottom - rect.top,
            "left": rect.left, "top": rect.top,
        })
        return True

    user32.EnumWindows(EnumProc(cb), 0)
    return out


def find_window(title_keyword: str, pid: int = 0, min_w: int = 200, visible_only: bool = True) -> dict | None:
    cands = [r for r in list_windows(title_keyword, pid)
             if r["w"] >= min_w and (r["visible"] or not visible_only)]
    cands.sort(key=lambda r: r["w"] * r["h"], reverse=True)
    return cands[0] if cands else None


def _capture_printwindow(hwnd: int, width: int, height: int):
    hwnd_dc = user32.GetWindowDC(hwnd)
    mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    gdi32.SelectObject(mfc_dc, bmp)
    ok = user32.PrintWindow(hwnd, mfc_dc, PW_RENDERFULLCONTENT)
    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetBitmapBits(bmp, len(buf), buf)
    img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mfc_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    return img if ok else None


def _capture_screen(left: int, top: int, width: int, height: int):
    screen_dc = user32.GetDC(0)
    mfc_dc = gdi32.CreateCompatibleDC(screen_dc)
    bmp = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    gdi32.SelectObject(mfc_dc, bmp)
    gdi32.BitBlt(mfc_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY | CAPTUREBLT)
    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetBitmapBits(bmp, len(buf), buf)
    img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mfc_dc)
    user32.ReleaseDC(0, screen_dc)
    return img


def capture(hwnd: int, allow_fallback: bool = True):
    """截窗口。返回 RGB 图。

    先试 PrintWindow；Qt 程序常返回纯黑，此时**必须**先把窗口切到前台
    再走屏幕截图，否则 BitBlt 会截到压在上面的别的窗口。
    """
    win = next((r for r in list_windows() if r["hwnd"] == hwnd), None)
    if not win:
        raise RuntimeError("窗口不存在")
    width, height = win["w"], win["h"]
    img = _capture_printwindow(hwnd, width, height)
    if img is not None and not _is_blank(img):
        return img.convert("RGB")
    if not allow_fallback:
        raise RuntimeError("PrintWindow 返回空图，且不允许退回屏幕截图")
    focus(hwnd)
    time.sleep(0.35)
    win = next((r for r in list_windows() if r["hwnd"] == hwnd), win)
    img = _capture_screen(win["left"], win["top"], win["w"], win["h"])
    return img.convert("RGB")


def _is_blank(img: Image.Image) -> bool:
    """PrintWindow 对 Qt 程序常返回纯黑，用它判断是否需要退回屏幕截图。"""
    small = img.convert("L").resize((64, 64))
    data = small.tobytes()
    return max(data) < 12


def save(img: Image.Image, name: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / name
    img.save(path)
    return path


def click(hwnd: int, x: int, y: int, wait: float = 1.2) -> None:
    """在窗口客户区内点击（x, y 相对窗口左上角）。"""
    left = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(left))
    sx, sy = left.left + int(x), left.top + int(y)
    user32.SetCursorPos(sx, sy)
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFT DOWN
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFT UP
    time.sleep(wait)


def scroll(hwnd: int, x: int, y: int, notches: int = -3, wait: float = 0.8) -> None:
    """滚轮滚动；notches 负数向下。"""
    left = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(left))
    user32.SetCursorPos(left.left + int(x), left.top + int(y))
    time.sleep(0.1)
    user32.mouse_event(0x0800, 0, 0, notches * 120, 0)  # MOUSEEVENTF_WHEEL
    time.sleep(wait)


def focus(hwnd: int) -> None:
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.6)


def type_text(text: str) -> None:
    """输入文字（仅 ASCII 可靠；中文用剪贴板）。"""
    for ch in text:
        user32.keybd_event(0, 0, 0, 0)
    # 走剪贴板粘贴更稳
    set_clipboard(text)
    key_combo(0x11, 0x56)  # Ctrl+V


def set_clipboard(text: str) -> None:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    kernel32 = ctypes.windll.kernel32
    # 64 位下必须声明返回类型，否则句柄被截断成 32 位，memmove 会写到空指针
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p

    if not user32.OpenClipboard(0):
        raise RuntimeError("打开剪贴板失败")
    try:
        user32.EmptyClipboard()
        size = (len(text) + 1) * 2
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            raise RuntimeError("锁定剪贴板内存失败")
        ctypes.memmove(ptr, ctypes.create_unicode_buffer(text), size)
        kernel32.GlobalUnlock(handle)
        user32.SetClipboardData(CF_UNICODETEXT, handle)
    finally:
        user32.CloseClipboard()


def get_clipboard() -> str:
    CF_UNICODETEXT = 13
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p

    if not user32.OpenClipboard(0):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        text = ctypes.wstring_at(ptr) if ptr else ""
        kernel32.GlobalUnlock(handle)
        return text or ""
    finally:
        user32.CloseClipboard()


def key_combo(*keys: int) -> None:
    for k in keys:
        user32.keybd_event(k, 0, 0, 0)
    for k in reversed(keys):
        user32.keybd_event(k, 0, 0x0002, 0)
    time.sleep(0.3)
