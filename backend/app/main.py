"""群组聚餐组队微信小程序 - FastAPI 入口。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(api_router, prefix=settings.api_prefix)

# 上传文件静态服务（头像）：目录不存在时创建，避免启动失败
uploads_root = Path(settings.uploads_dir)
uploads_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_root)), name="uploads")
