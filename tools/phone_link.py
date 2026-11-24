"""安卓手机自动取视频号作品链接：看界面找文字，不写死按钮坐标。

流程：微信 → 发现 → 视频号 → 搜索标题 → 账号主页 → 点中目标作品 →
分享 → 第三排左滑 → 复制链接 → Chrome 粘贴 → OCR 读出短链。

用法：python tools/phone_link.py "作品标题"
"""
from __future__ import annotations

import base64
import subprocess
import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import phone_ui as ui

ADB = str(ui.ADB)


class LinkError(RuntimeError):
    pass


def device_ids() -> list[str]:
    out = subprocess.run([ADB, "devices"], capture_output=True).stdout.decode()
    return [line.split()[0] for line in out.splitlines()[1:] if line.split()[-1:] == ["device"]]


def input_text(device: str, text: str) -> None:
    b64 = base64.b64encode(text.encode("utf-8")).decode()
    ui.adb(device, "shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64)


def _tap(device: str, item: dict, wait: float = 1.0) -> None:
    ui.adb(device, "shell", "input", "tap", str(item["cx"]), str(item["cy"]))
    time.sleep(wait)


def _find_or_none(device: str, keyword: str) -> dict | None:
    items, _, _ = ui.read(device)
    hits = ui.find(items, keyword)
    return hits[0] if hits else None


def _focus(device: str) -> str:
    out = ui.adb(device, "shell", "dumpsys", "window")
    for line in out.splitlines():
        if "mCurrentFocus" in line:
            return line.strip()
    return ""


def open_profile(device: str, account: str) -> None:
    # 直接冷启动微信，保证回到聊天列表，避免停在某个聊天里
    ui.adb(device, "shell", "am", "force-stop", "com.tencent.mm")
    time.sleep(1.5)
    ui.adb(device, "shell", "am", "start", "-n", "com.tencent.mm/.ui.LauncherUI")
    time.sleep(4.0)
    # 主界面底部「发现」是图标+小字，OCR 不稳，按比例点
    ui.tap_ratio(device, 0.62, 0.95, wait=1.5)
    # 发现页的「视频号」文字较大，用 OCR；找不到再按比例
    try:
        ui.tap_text(device, "视频号", wait=4.5)
    except ui.UIFail:
        ui.tap_ratio(device, 0.284, 0.197, wait=4.5)
    # 搜索图标在「推荐 / 关注」右边固定距离；先认字，避免布局变化点空
    items, width, _ = ui.read(device)
    anchor = ui.find(items, "推荐") or ui.find(items, "关注")
    if anchor:
        x = int(width * 0.837)
        y = anchor[0]["cy"]
        ui.adb(device, "shell", "input", "tap", str(x), str(y))
        time.sleep(2.0)
    else:
        ui.tap_ratio(device, 0.837, 0.035, wait=2.0)
    ui.tap_ratio(device, 0.37, 0.071, wait=0.8)
    ui.adb(device, "shell", "input", "keyevent", "123")
    for _ in range(40):
        ui.adb(device, "shell", "input", "keyevent", "67")
    input_text(device, account)
    time.sleep(0.8)
    search = _find_or_none(device, "搜索")
    if not search:
        raise LinkError("搜索页没找到「搜索」按钮")
    _tap(device, search, wait=4.0)
    # 账号卡片 → 账号主页
    card = _find_or_none(device, "前往账号主页")
    if card:
        _tap(device, card, wait=4.0)
    else:
        # 搜索结果直接是视频时，退回账号页不可用
        raise LinkError("搜索结果里没有账号主页入口")


def tap_video_on_profile(device: str, title: str) -> None:
    target = ui.norm(title)[:6]
    for _ in range(6):
        items, _, _ = ui.read(device)
        for item in items:
            if target and target in ui.norm(item["text"]):
                _tap(device, item, wait=3.5)
                # 打开后核对视频页文案，防止点到的只是封面相似的别的作品
                opened, _, _ = ui.read(device)
                if ui.find(opened, title[:8]):
                    return
                ui.adb(device, "shell", "input", "keyevent", "4")
                time.sleep(1.2)
        ui.swipe_ratio(device, 0.5, 0.78, 0.5, 0.35, ms=450, wait=1.2)
    raise LinkError("账号主页里没找到这条作品（可能需要继续下滑）")


def copy_share_link(device: str) -> None:
    ui.tap_ratio(device, 0.672, 0.928, wait=2.0)
    for _ in range(4):
        items, _, _ = ui.read(device)
        hit = ui.find(items, "复制链接")
        if hit:
            _tap(device, hit[0], wait=1.5)
            return
        ui.swipe_ratio(device, 0.85, 0.80, 0.12, 0.80, ms=400, wait=0.8)
    raise LinkError("分享面板里没找到「复制链接」")


def read_clipboard(device: str) -> str:
    ui.adb(device, "shell", "monkey", "-p", "com.android.chrome",
           "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(2.5)
    ui.tap_ratio(device, 0.46, 0.30, wait=0.8)
    ui.adb(device, "shell", "input", "keyevent", "279")
    time.sleep(1.2)
    items, _, _ = ui.read(device)
    link = ui.find_link(items)
    if not link:
        raise LinkError("粘贴后没读到链接")
    return link


def copy_link_for_title(account: str, title: str) -> str:
    devs = device_ids()
    if not devs:
        raise LinkError("没有已连接的手机")
    device = devs[0]
    # 保持亮屏，否则自动化中途熄屏会全部失败
    ui.adb(device, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    ui.adb(device, "shell", "wm", "dismiss-keyguard")
    ui.adb(device, "shell", "settings", "put", "system", "screen_off_timeout", "600000")
    time.sleep(0.8)
    open_profile(device, account)
    tap_video_on_profile(device, title)
    copy_share_link(device)
    return read_clipboard(device)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('用法: python tools/phone_link.py "账号昵称" "作品标题"')
        raise SystemExit(2)
    try:
        print(copy_link_for_title(sys.argv[1], sys.argv[2]))
    except (LinkError, ui.UIFail) as exc:
        print("失败:", exc)
        raise SystemExit(1)
