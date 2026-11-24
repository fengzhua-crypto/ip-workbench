"""阶段 1 核心验证：截获视频号助手数据中心页面的数据接口响应。

用法：python tools/probe_net.py <页面地址> [--wait 20]
产物：data\probe\<时间戳>\net\*.json（接口原始响应）+ summary.txt
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "data" / "auth" / "chrome-profile"

KEEP = re.compile(r"(statistic|stat|follower|data|metric|overview|trend|summary)", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait", type=int, default=20)
    args = ap.parse_args()

    out = ROOT / "data" / "probe" / datetime.now().strftime("%Y%m%d-%H%M%S")
    net = out / "net"
    net.mkdir(parents=True, exist_ok=True)
    summary: list[str] = []
    saved = 0

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=True,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def on_response(resp):
            nonlocal saved
            try:
                ctype = (resp.headers.get("content-type") or "").lower()
                if "json" not in ctype:
                    return
                url = resp.url
                if "channels.weixin.qq.com" not in url:
                    return
                body = resp.text()
                if not body or len(body) < 20:
                    return
                data = json.loads(body)
                try:
                    title = (data.get("data") or {}).get("errMsg", "")
                except Exception:
                    title = ""
                name = re.sub(r"[^a-zA-Z0-9]+", "_", url.split("?")[0].split("/")[-1])[:60] or "api"
                fn = net / f"{saved:02d}_{name}.json"
                req = resp.request
                fn.write_text(json.dumps({"url": url, "method": req.method,
                                          "post_data": req.post_data,
                                          "data": data}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
                saved += 1
                summary.append(f"[{saved:02d}] {url}  ({len(body)} bytes)")
            except Exception:
                pass

        page.on("response", on_response)

        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(args.wait * 1000)
            # 尝试滚动，触发懒加载
            for _ in range(3):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(1500)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(out / "page.png"), full_page=True)
            (out / "page.txt").write_text(
                "\n".join(page.evaluate("() => [document.body.innerText]")), encoding="utf-8"
            )
        finally:
            (out / "summary.txt").write_text("\n".join(summary), encoding="utf-8")
            ctx.close()

    print(f"截获 {saved} 个接口响应")
    for line in summary:
        print("  " + line)
    print(f"产物目录：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
