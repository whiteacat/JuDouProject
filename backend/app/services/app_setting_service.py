"""应用配置服务：读取/更新开关配置。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting, DEFAULTS, KEY_CONTENT_EDIT_ENABLED


async def get_setting_bool(db: AsyncSession, key: str) -> bool:
    """读取布尔开关；未配置时返回默认值。"""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is not None:
        return setting.value
    default = DEFAULTS.get(key)
    return bool(default["value"]) if default else True


async def set_setting_bool(db: AsyncSession, key: str, value: bool) -> None:
    """更新布尔开关（upsert）。"""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        default = DEFAULTS.get(key, {"value": value, "description": None})
        setting = AppSetting(
            key=key,
            value=value,
            description=default.get("description"),
        )
        db.add(setting)
    else:
        setting.value = value
    await db.commit()


async def is_content_edit_enabled(db: AsyncSession) -> bool:
    """内容编辑总开关是否开启。"""
    return await get_setting_bool(db, KEY_CONTENT_EDIT_ENABLED)


async def ensure_content_edit_enabled(db: AsyncSession) -> None:
    """内容编辑开关守卫：关闭时抛出 403。

    在用户文本写入的服务层（create_group / create_event /
    submit_review / update_user_profile 等）调用，作为服务端统一拦截点。
    """
    if not await is_content_edit_enabled(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="平台内容编辑功能已暂停，暂不可提交",
        )
