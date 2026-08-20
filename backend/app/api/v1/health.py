"""健康检查：验证服务与数据库（含 PostGIS）连通性。"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_ok = False
    postgis_version: str | None = None
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        result = await db.execute(text("SELECT postgis_version()"))
        value = result.scalar()
        if value:
            postgis_version = str(value)
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "postgis": postgis_version,
    }
