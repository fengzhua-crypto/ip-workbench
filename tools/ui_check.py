"""用无头浏览器打开工作台，检查页面是否正常渲染、有没有 JS 报错。

只读本地页面，不调用任何付费接口。
用法：python tools/ui_check.py [--shot 输出名]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8741"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "exports"


def run(shot: str = "") -> int:
    errors: list[str] = []
    with sync_playwright() as p:
        # 用本机已装的 Chrome（项目其它模块也是 channel="chrome"），
        # 不额外下载 Playwright 自带浏览器
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        page.goto(BASE, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1200)

        title = page.title()
        # 主容器有没有内容
        body_text = page.inner_text("body")[:200].replace("\n", " ")
        print(f"页面标题：{title}")
        print(f"首屏文字：{body_text[:120]}")

        # 进「对标拆解」
        clicked = False
        for label in ("对标拆解", "拆解"):
            try:
                page.get_by_text(label, exact=True).first.click(timeout=3000)
                clicked = True
                break
            except Exception:
                continue
        page.wait_for_timeout(1500)
        print("进入对标拆解：", "成功" if clicked else "失败")

        if clicked:
            text = page.inner_text("body")
            for kw in ("视频拆解", "账号拆解", "全部", "进行中"):
                print(f"  含「{kw}」：", kw in text)
            # 切到账号拆解
            try:
                page.get_by_text("账号拆解", exact=True).first.click(timeout=3000)
                page.wait_for_timeout(1800)
                text2 = page.inner_text("body")
                for kw in ("对标账号", "添加账号", "近一年", "双榜", "作品列表"):
                    print(f"  账号页含「{kw}」：", kw in text2)
            except Exception as exc:
                print("  切账号拆解失败：", str(exc)[:80])

        name = shot or "ui_check.png"
        path = OUT / name
        OUT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=False)
        print("截图：", path)

        browser.close()

    if errors:
        print("\n发现前端错误：")
        for e in errors[:20]:
            print("  -", e[:300])
        return 1
    print("\n没有前端报错")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default="")
    sys.exit(run(ap.parse_args().shot))
