"""站内通知模型：每用户一条通知流（服务端事件驱动写入）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_user", "user_id", "is_read", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 接收人
    user_id: Mapped[int] = mapped_column(BigInteger)
    # 通知类型（event_confirmed / event_cancelled / event_completed /
    # member_joined / member_left / new_review / system 等）
    type: Mapped[str] = mapped_column(String(32))
    # 短标题（列表页小标题）
    title: Mapped[str] = mapped_column(String(64))
    # 渲染后的完整文案
    content: Mapped[str] = mapped_column(Text)
    # 跳转目标
    target_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 触发动作的用户（冗余昵称，防历史文案随昵称漂移）
    actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
