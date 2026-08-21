"""健康检查：验证服务与数据库（含 PostGIS）连通性。"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_ok = False
    postgis_version: str | None = None
    db_error: str | None = None
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        result = await db.execute(text("SELECT postgis_version()"))
        value = result.scalar()
        if value:
            postgis_version = str(value)
    except Exception as exc:
        # 暴露数据库连接失败原因，便于部署环境排障
        db_error = str(exc)[:300]
        logger.error("health check db failed: %s", db_error)
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "postgis": postgis_version,
        "db_error": db_error,
    }
