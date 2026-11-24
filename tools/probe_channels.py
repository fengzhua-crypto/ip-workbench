"""阶段 1 探测脚本：验证视频号助手后台能否自动读取数据。

用法：
    python tools/probe_channels.py            # 打开窗口，扫码登录，保存首页结构
    python tools/probe_channels.py --check    # 不发请求，只报告登录态是否还在

产物保存在 data\probe\<时间戳>\ 下：截图、页面 HTML、可点击菜单清单、运行日志。
登录态保存在 data\auth\chrome-profile\（独立的浏览器用户目录，与日常 Chrome 互不影响）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "data" / "auth" / "chrome-profile"
LOGIN_URL = "https://channels.weixin.qq.com/platform"
LOGIN_WAIT_MINUTES = 10


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _open(p):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel="chrome",
        headless=False,
        no_viewport=True,
        args=["--disable-blink-features=AutomationControlled"],
    )


def _is_logged_in(page) -> bool:
    url = page.url
    if "login.html" in url:
        return False
    try:
        text = page.inner_text("body")[:2000]
    except Exception:
        text = ""
    return "登录" not in text[:200] and len(text) > 200


def _dump(page, out: Path, name: str) -> None:
    (out / f"{name}.html").write_text(page.content(), encoding="utf-8")
    (out / f"{name}.txt").write_text(page.inner_text("body"), encoding="utf-8")
    page.screenshot(path=str(out / f"{name}.png"), full_page=True)


def _collect_links(page) -> list[dict]:
    items = page.eval_on_selector_all(
        "a, [role=menuitem], [class*=menu] a, [class*=nav] a",
        """els => els.map(e => ({
            tag: e.tagName,
            text: (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
            href: e.getAttribute('href') || '',
            cls: (e.className && e.className.toString ? e.className.toString() : '').slice(0, 80)
        })).filter(x => x.text || x.href)""",
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
    ap.add_argument("--check", action="store_true", help="只检查登录态")
    ap.add_argument("--wait-minutes", type=int, default=LOGIN_WAIT_MINUTES)
    args = ap.parse_args()

    out = ROOT / "data" / "probe" / _stamp()
    out.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log_lines.append(line)

    log(f"产物目录：{out}")
    log(f"登录态目录：{PROFILE_DIR}")

    with sync_playwright() as p:
        ctx = _open(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            logged = _is_logged_in(page)

            if args.check:
                log(f"登录态：{'有效' if logged else '已失效'}")
                _dump(page, out, "check")
                return 0

            if not logged:
                log("=" * 60)
                log("请在刚弹出的 Chrome 窗口里，用微信扫码登录视频号助手。")
                log(f"最多等待 {args.wait_minutes} 分钟；登录成功后脚本会自动继续。")
                log("=" * 60)
                waited = 0
                while waited < args.wait_minutes * 60:
                    page.wait_for_timeout(2000)
                    waited += 2
                    if _is_logged_in(page):
                        log(f"已检测到登录（等待 {waited} 秒）")
                        break
                else:
                    log("等待超时：没有检测到登录，已退出。")
                    return 2
            else:
                log("登录态有效，直接进入。")

            page.wait_for_timeout(3000)
            log(f"当前页面：{page.url}")
            _dump(page, out, "home")

            links = _collect_links(page)
            (out / "links.json").write_text(
                json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"收录可点击项 {len(links)} 个，已保存 links.json")

            nav_text = [l["text"] for l in links if l["text"]]
            log("页面可见菜单/链接文字：")
            for t in nav_text[:60]:
                log(f"  - {t}")

            (out / "log.txt").write_text("\n".join(log_lines), encoding="utf-8")
            log("阶段 1 第一轮采集完成。")
            return 0
        finally:
            try:
                (out / "log.txt").write_text("\n".join(log_lines), encoding="utf-8")
            except Exception:
                pass
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
