"""本地启动入口：只监听 127.0.0.1，纯 API 模式。

用法（在 media-parser 目录下）：
    .venv\\Scripts\\python.exe run_local.py
"""
from __future__ import annotations

import os

os.environ.setdefault("API_ONLY", "true")

from app import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", "8051"))
    app.run(host="127.0.0.1", port=port, threaded=True)
