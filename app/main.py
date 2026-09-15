"""ShortLink Demo 入口：FastAPI 应用装配。"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import api, pages, redirect
from .tasks import sync_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（演示项目不引入迁移工具）
    Base.metadata.create_all(bind=engine)

    sync_task = None
    if settings.sync_task_enabled:
        sync_task = asyncio.create_task(sync_loop(settings.sync_interval))
        logging.getLogger(__name__).info("点击计数同步任务已启动，间隔 %.1fs", settings.sync_interval)

    yield

    if sync_task:
        sync_task.cancel()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="短链接生成与统计平台：长链接转短链、302 跳转、点击统计、Redis 缓存、IP 限流。",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(api.router, prefix="/api")
app.include_router(redirect.router)
app.include_router(pages.router)
