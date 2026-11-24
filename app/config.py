"""应用配置：路径、端口、运行模式。"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "IP 运营工作台"
APP_VERSION = "0.17.1"
BUILD_PROFILE = "local"

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def _data_dir() -> Path:
    """数据默认放在项目内的 data/ 目录，整个项目可整体备份、迁移。"""
    env = os.environ.get("IPWB_DATA_DIR")
    if env:
        return Path(env)
    return ROOT_DIR / "data"


DATA_DIR = _data_dir()
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "app.db"
PORT = int(os.environ.get("IPWB_PORT", "8741"))
DEMO_MODE = os.environ.get("IPWB_DEMO", "1") != "0"
SYNC_TIME = os.environ.get("IPWB_SYNC_TIME", "08:30")

UPLOAD_LIMIT_MB = 500


def ensure_dirs() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR, DATA_DIR / "shots"):
        path.mkdir(parents=True, exist_ok=True)


ensure_dirs()
