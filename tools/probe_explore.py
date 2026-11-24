"""阶段 1 辅助脚本：从视频号助手首页用菜单点击逐层进入数据中心并留档。

用法：python tools/probe_explore.py
产物：data\probe\<时间戳>\，每步一张截图 + HTML + 可见文本。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "data" / "auth" / "chrome-profile"
HOME = "https://channels.weixin.qq.com/platform"

STEPS = ["数据中心", "关注者数据", "视频数据", "图文数据"]


def _dump(page, out: Path, name: str) -> None:
    (out / f"{name}.html").write_text(page.content(), encoding="utf-8")
    (out / f"{name}.txt").write_text(page.inner_text("body"), encoding="utf-8")
    page.screenshot(path=str(out / f"{name}.png"), full_page=True)


def _click_text(page, text: str) -> bool:
    candidates = [
        page.get_by_text(text, exact=True),
        page.get_by_text(text, exact=False),
        page.locator(f"text={text}"),
    ]
    for loc in candidates:
        try:
            if loc.count() == 0:
                continue
            loc.first.click(timeout=6000)
            return True
        except Exception:
            continue
    return False


def main() -> int:
    out = ROOT / "data" / "probe" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    report: list[str] = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            if "login.html" in page.url:
                print("[FAIL] 登录态失效，需要重新扫码。", flush=True)
                return 2

            for i, step in enumerate(STEPS):
                ok = _click_text(page, step)
                page.wait_for_timeout(4000)
                name = f"{i}_{step}"
                _dump(page, out, name)
                line = f"{step}: click={'ok' if ok else 'fail'} url={page.url}"
                print("[STEP] " + line, flush=True)
                report.append(line)
                if not ok:
                    print(f"[SKIP] 找不到或点不到「{step}」，后续步骤继续尝试。", flush=True)

            # 记录当前页所有可见菜单与链接，便于后续定位
            links = page.eval_on_selector_all(
                "a, [class*=menu] *, [class*=tab]",
                """els => els.map(e => ({
                    t: (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40),
                    h: e.getAttribute('href') || '',
                    c: (e.className && e.className.toString ? e.className.toString() : '').slice(0, 70)
                })).filter(x => x.t && x.t.length < 40)""",
            )
            seen, uniq = set(), []
            for it in links:
                k = (it["t"], it["h"])
                if k not in seen:
                    seen.add(k)
                    uniq.append(it)
            (out / "menus.json").write_text(
                json.dumps(uniq, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"产物目录：{out}", flush=True)
            return 0
        finally:
            ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())
