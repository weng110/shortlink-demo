"""pytest 全局配置：SQLite + fakeredis 跑全流程，不依赖 Docker。"""

import os

# 必须在导入 app 之前设置环境变量（config.Settings 在导入时读取）
os.environ["DATABASE_URL"] = "sqlite:///./test_shortlink.db"
os.environ["SYNC_TASK_ENABLED"] = "false"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Link  # noqa: E402
from app.redis_client import redis_holder  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture()
def client():
    """每个测试独立的 fakeredis + 清空数据表，保证隔离。"""
    redis_holder.set(fakeredis.FakeRedis(decode_responses=True))
    with TestClient(app) as c:
        db = SessionLocal()
        try:
            db.query(Link).delete()
            db.commit()
        finally:
            db.close()
        yield c
    redis_holder.set(None)
