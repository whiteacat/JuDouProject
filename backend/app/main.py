"""群组聚餐组队微信小程序 - FastAPI 入口。"""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(api_router, prefix=settings.api_prefix)
