"""IP 运营工作台 · 本地服务入口。

启动后浏览器会自动打开 http://127.0.0.1:8741
"""
from __future__ import annotations

import os
import threading
import webbrowser

import uvicorn

from app import config


def _open_browser() -> None:
    try:
        webbrowser.open(f"http://127.0.0.1:{config.PORT}")
    except Exception:
        pass


def main() -> None:
    print("=" * 56)
    print(f"  {config.APP_NAME}  v{config.APP_VERSION}")
    print(f"  数据目录：{config.DATA_DIR}")
    print(f"  访问地址：http://127.0.0.1:{config.PORT}")
    print("  关闭窗口或按 Ctrl+C 停止服务")
    print("=" * 56)
    if os.environ.get("IPWB_NO_BROWSER", "") != "1":
        threading.Timer(1.2, _open_browser).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=config.PORT, log_level="info")


if __name__ == "__main__":
    main()
