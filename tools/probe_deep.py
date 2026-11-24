"""阶段 1 辅助脚本：进入数据中心子页面，穿透 iframe / shadow DOM 提取可见文本。

用法：python tools/probe_deep.py 关注者数据 视频数据
产物：data\probe\<时间戳>\<步骤>.txt / .png / .html
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "data" / "auth" / "chrome-profile"
HOME = "https://channels.weixin.qq.com/platform"

DEEP_TEXT = """
(root) => {
  const out = [];
  const skip = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'svg']);
  const walk = (node) => {
    if (!node) return;
    if (node.nodeType === 3) {
      const s = (node.textContent || '').trim();
      if (s) out.push(s);
      return;
    }
    if (node.nodeType === 1 && skip.has(node.tagName)) return;
    for (const c of node.childNodes) walk(c);
    if (node.shadowRoot) walk(node.shadowRoot);
  };
  walk(root);
  return out;
}
"""


def _click(page, text: str) -> bool:
    for loc in (page.get_by_text(text, exact=True), page.get_by_text(text, exact=False)):
        try:
            if loc.count():
                loc.first.click(timeout=6000)
                return True
        except Exception:
            continue
    return False


def _deep_text(target) -> list[str]:
    try:
        parts = target.evaluate(f"({DEEP_TEXT})(document)") or []
    except Exception:
        return []
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def main() -> int:
    steps = sys.argv[1:] or ["关注者数据", "视频数据"]
    out = ROOT / "data" / "probe" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)

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

            for step in steps:
                if step.startswith("http"):
                    page.goto(step, wait_until="domcontentloaded", timeout=60000)
                    ok = True
                else:
                    _click(page, "数据中心")
                    page.wait_for_timeout(1200)
                    ok = _click(page, step)
                page.wait_for_timeout(3000)
                # 等子应用渲染：最多等 25 秒，直到文本明显变多
                best = 0
                for _ in range(10):
                    page.wait_for_timeout(2500)
                    parts = []
                    for f in page.frames:
                        parts += _deep_text(f)
                    if len(parts) > best + 10:
                        best = len(parts)
                print(f"[STEP] {step} click={ok} url={page.url} 文本片段={best}", flush=True)

                texts = []
                for f in page.frames:
                    seg = _deep_text(f)
                    if seg:
                        texts.append(f"--- frame: {f.url or f.name} ---")
                        texts += seg
                (out / f"{step.replace(':','').replace('/','_')[-40:]}.txt").write_text("\n".join(texts), encoding="utf-8")
                page.screenshot(path=str(out / f"{step.replace(':','').replace('/','_')[-40:]}.png"), full_page=True)
                (out / f"{step.replace(':','').replace('/','_')[-40:]}.html").write_text(page.content(), encoding="utf-8")
            print(f"产物目录：{out}", flush=True)
            return 0
        finally:
            ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())
