"""手机采集：进账号主页 → 视频 → 一路下滑，读日期和转发数，达标就复制链接。

不设条数上限：只有滑到超过指定天数才停。
链接由 AutoJs6（悬浮窗保持后台）自动回传到工作台。
用法：python tools/phone_collect.py "账号昵称" 30 100
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phone_ui as ui
import phone_link as pl

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
AGE_RE = re.compile(r"(\d+)\s*天前")
MONTH_RE = re.compile(r"(\d+)\s*个月前")
NUM_RE = re.compile(r"^(\d+(?:\.\d+)?)(万|w|W)?$")


def _num(text: str) -> float | None:
    m = NUM_RE.match(text.strip())
    if not m:
        return None
    value = float(m.group(1))
    if m.group(2):
        value *= 10000
    return value


def _age(items: list[dict]) -> tuple[str, int | None]:
    for item in items:
        text = item["text"]
        m = AGE_RE.search(text)
        if m:
            return text, int(m.group(1))
        if "昨天" in text:
            return text, 1
        if "前天" in text:
            return text, 2
        if MONTH_RE.search(text) or "年前" in text:
            return text, 999
        m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
        if m:
            now = time.localtime()
            month, day = int(m.group(1)), int(m.group(2))
            try:
                stamp = time.mktime((now.tm_year, month, day, 0, 0, 0, 0, 0, -1))
                if stamp > time.time() + 86400:
                    stamp = time.mktime((now.tm_year - 1, month, day, 0, 0, 0, 0, 0, -1))
                return text, int((time.time() - stamp) / 86400)
            except Exception:
                pass
        m = DATE_RE.search(text)
        if m:
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            try:
                age = (time.time() - time.mktime(time.strptime(date, "%Y-%m-%d"))) / 86400
                return date, int(age)
            except Exception:
                return date, None
    return "", None


def _share_count(device: str, width: int, height: int) -> tuple[float | None, list[str]]:
    """只认底部那一行的数字；按横坐标定位「转发」（第二个数）。"""
    best = None
    raw: list[str] = []
    for _ in range(2):
        items, w, h = ui.read(device)
        width, height = w, h
        nums = []
        for it in items:
            if it["cy"] > height * 0.80 and _num(it["text"]) is not None:
                nums.append(it)
        nums.sort(key=lambda it: it["cx"])
        raw = [it["text"] for it in nums]
        if len(nums) >= 2:
            if len(nums) >= 4:
                best = _num(nums[1]["text"])
            else:
                near = min(nums, key=lambda it: abs(it["cx"] - width * 0.60))
                if abs(near["cx"] - width * 0.60) < width * 0.10:
                    best = _num(near["text"])
            if best is not None:
                return best, raw
        time.sleep(1.2)
    return best, raw


def _open_video_tab(device: str) -> None:
    items, _, _ = ui.read(device)
    for it in items:
        if ui.norm(it["text"]) == "视频" and 1000 < it["cy"] < 1400:
            ui.adb(device, "shell", "input", "tap", str(it["cx"]), str(it["cy"]))
            time.sleep(2.5)
            return
    ui.tap_ratio(device, 0.22, 0.50, wait=2.5)


def collect(account: str, days: int, min_shares: int) -> list[dict]:
    devs = pl.device_ids()
    if not devs:
        raise SystemExit("没有已连接的手机")
    device = devs[0]
    ui.adb(device, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    ui.adb(device, "shell", "wm", "dismiss-keyguard")
    ui.adb(device, "shell", "settings", "put", "system", "screen_off_timeout", "600000")

    last_error = ""
    for _ in range(3):
        try:
            pl.open_profile(device, account)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(2)
    else:
        raise SystemExit(f"进账号主页失败：{last_error}")

    items, _, _ = ui.read(device)
    pinned = sum(1 for it in items if ui.norm(it["text"]).startswith("置顶"))
    print(f"置顶 {pinned} 条", flush=True)
    _open_video_tab(device)
    ui.tap_ratio(device, 0.17, 0.62, wait=3.0)

    rows = []
    unknown = 0
    for index in range(120):  # 安全上限，真正停止条件是日期边界
        items, width, height = ui.read(device)
        date, age_days = _age(items)
        is_pinned = index < pinned
        if age_days is not None and age_days > days and not is_pinned:
            print(f"到边界：{date}（{age_days} 天前），停止", flush=True)
            break
        shares, raw = _share_count(device, width, height)
        print(f"[{index + 1}] {date or '?'} 转发={shares} 原始={raw}", flush=True)
        row = {"date": date, "age": age_days, "shares": shares,
               "pinned": is_pinned, "raw": raw}
        if shares is None:
            unknown += 1
        elif shares >= min_shares:
            pl.copy_share_link(device)
            row["copied"] = True
            print("  → 达标，已复制链接", flush=True)
            time.sleep(1.6)
        rows.append(row)
        ui.swipe_ratio(device, 0.5, 0.82, 0.5, 0.28, ms=500, wait=2.2)

    path = Path(__file__).resolve().parent.parent / "data" / "exports" / "phone_collect.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：共检查 {len(rows)} 条，数字未识别 {unknown} 条", flush=True)
    return rows


if __name__ == "__main__":
    account = sys.argv[1] if len(sys.argv) > 1 else "玖妈懂敏宝"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    min_shares = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    collect(account, days, min_shares)
