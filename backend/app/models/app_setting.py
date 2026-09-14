"""应用运行配置模型（键值对，存于 app_settings 表）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSetting(Base):
    """通用开关/配置项。

    当前用途：content_edit_enabled 总开关——
    关闭后拒绝所有用户可编辑文本的提交（群组名、活动、评价、昵称/签名等）。
    """

    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_app_settings_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # bool 型开关值
    value: Mapped[bool] = mapped_column(Boolean, default=True)
    # 文本型配置（如公告文案），与 value 二选一使用
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ── 配置键常量 ─────────────────────────────────────────────────

# 内容编辑总开关（前期内容安全防控：关闭后所有用户文本提交被拒绝）
KEY_CONTENT_EDIT_ENABLED = "content_edit_enabled"

DEFAULTS: dict[str, dict] = {
    KEY_CONTENT_EDIT_ENABLED: {
        "value": True,
        "description": "用户内容编辑总开关（群组名/活动/评价/昵称签名）",
    }
}
