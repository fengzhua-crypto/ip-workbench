"""FastAPI 应用装配。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, scheduler
from .api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    db.seed_demo()
    db.reset_stale_transcribing()
    db.reset_stale_decompositions()
    scheduler.start()
    yield
    scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=lifespan)
    app.include_router(router)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        # 本地单用户应用：页面和静态资源一律不缓存，
        # 避免改了前端却因为浏览器缓存看不到新界面
        if request.url.path.startswith(("/assets/", "/media/")) or request.url.path == "/":
            response.headers["Cache-Control"] = "no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response

    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIR / "assets"), name="assets")
    app.mount("/media/shots", StaticFiles(directory=config.DATA_DIR / "shots"), name="shots")

    @app.get("/{full_path:path}")
    def index(full_path: str = ""):
        return FileResponse(config.FRONTEND_DIR / "index.html")

    return app


app = create_app()
