"""阶段 1 辅助脚本：用已保存的登录态访问指定页面并留档。

用法：
    python tools/probe_page.py <url> [<url> ...] [--click 文字]

每个 url 会保存 截图 / HTML / 可见文本 / 可点击项 到 data\probe\<时间戳>\。
加了 --click 时，访问完 url 后再点击页面里文字包含该词的菜单项，并留档。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "data" / "auth" / "chrome-profile"


def _slug(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1] or "root"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in tail)[:40]


def _dump(page, out: Path, name: str) -> None:
    (out / f"{name}.html").write_text(page.content(), encoding="utf-8")
    (out / f"{name}.txt").write_text(page.inner_text("body"), encoding="utf-8")
    page.screenshot(path=str(out / f"{name}.png"), full_page=True)


def _links(page) -> list[dict]:
    items = page.eval_on_selector_all(
        "a, [role=menuitem], [class*=menu] a, [class*=nav] a, [class*=tab]",
        """els => els.map(e => ({
            text: (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
            href: e.getAttribute('href') || '',
            cls: (e.className && e.className.toString ? e.className.toString() : '').slice(0, 80)
        })).filter(x => x.text)""",
    )
    seen, uniq = set(), []
    for it in items:
        key = (it["text"], it["href"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--click", default="")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    out = ROOT / "data" / "probe" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=args.headless,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for url in args.urls:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
                name = _slug(url)
                print(f"[OK] {url} -> {name}.txt  title={page.title()!r}", flush=True)
                print(f"     url={page.url}", flush=True)
                _dump(page, out, name)
                links = _links(page)
                (out / f"{name}.links.json").write_text(
                    json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8"
                )

                if args.click:
                    for kw in [k for k in args.click.split(",") if k]:
                        try:
                            page.get_by_text(kw, exact=False).first.click(timeout=5000)
                            page.wait_for_timeout(3500)
                            cname = f"{name}_click_{kw}"
                            print(f"[OK] click {kw} -> {page.url}", flush=True)
                            _dump(page, out, cname)
                        except Exception as exc:
                            print(f"[SKIP] click {kw}: {exc.__class__.__name__}", flush=True)
        finally:
            ctx.close()
    print(f"产物目录：{out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
