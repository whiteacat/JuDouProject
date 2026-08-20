"""共享测试夹具：基于 httpx ASGI 客户端的应用级测试。"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import engine
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def require_db():
    """依赖真实数据库的用例：数据库不可达时跳过（本地需先起 docker 并跑迁移）。"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - 仅环境缺失时触发
        pytest.skip(f"database unavailable: {exc}")
    yield
