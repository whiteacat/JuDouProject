"""管理端配置 API：内容编辑总开关。

鉴权方式（前期安全防控）：
- 请求需携带 X-Admin-Key 请求头，与服务器 .env 的 ADMIN_KEY 一致
- ADMIN_KEY 未配置时，开关 API 一律 403（fail-closed，防止误操作）
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.app_setting import KEY_CONTENT_EDIT_ENABLED
from app.schemas.app_setting import SettingOut
from app.services import app_setting_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_key(admin_key: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_key
    if not expected:
        # 服务器未配置 ADMIN_KEY：开关 API 不可用（fail-closed）
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理密钥未配置，操作被拒绝",
        )
    if admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="管理密钥错误"
        )


@router.get("/status", response_model=SettingOut)
async def public_content_edit_status(
    db: AsyncSession = Depends(get_db),
) -> SettingOut:
    """公开只读端点：小程序查询内容编辑开关状态（无敏感信息）。"""
    enabled = await app_setting_service.is_content_edit_enabled(db)
    return SettingOut(key=KEY_CONTENT_EDIT_ENABLED, value=enabled)


@router.get(
    "/settings",
    response_model=SettingOut,
    dependencies=[Depends(_require_admin_key)],
)
async def get_content_edit_setting(
    db: AsyncSession = Depends(get_db),
) -> SettingOut:
    enabled = await app_setting_service.is_content_edit_enabled(db)
    return SettingOut(key=KEY_CONTENT_EDIT_ENABLED, value=enabled)


@router.put(
    "/settings",
    response_model=SettingOut,
    dependencies=[Depends(_require_admin_key)],
)
async def update_content_edit_setting(
    value: bool,
    db: AsyncSession = Depends(get_db),
) -> SettingOut:
    await app_setting_service.set_setting_bool(db, KEY_CONTENT_EDIT_ENABLED, value)
    return SettingOut(key=KEY_CONTENT_EDIT_ENABLED, value=value)
