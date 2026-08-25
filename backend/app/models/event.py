"""组队事件模型。"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventStatus:
    """组队事件状态机（后端统一控制）。"""

    RECRUITING = "RECRUITING"  # 招募中
    CONFIRMED = "CONFIRMED"  # 已满员确认
    COMPLETED = "COMPLETED"  # 聚餐完成
    CANCELLED = "CANCELLED"  # 已取消
    EXPIRED = "EXPIRED"  # 已失效（过期自动失效）


class ExpiryMode:
    """组队失效策略。"""

    NONE = "none"  # 长期有效
    AT_COMPLETE = "at_complete"  # 完成组队后才失效
    AT_TIME = "at_time"  # 指定时间失效（expires_at）
    AFTER_HOURS = "after_hours"  # 创建后 N 小时失效（创建时折算为 expires_at）


class GroupEvent(Base):
    __tablename__ = "group_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    creator_id: Mapped[int] = mapped_column(BigInteger)
    restaurant_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(64))
    event_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    min_members: Mapped[int] = mapped_column(Integer, default=1)
    max_members: Mapped[int] = mapped_column(Integer)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=EventStatus.RECRUITING)
    expiry_mode: Mapped[str] = mapped_column(
        String(16), default=ExpiryMode.NONE
    )
    # 失效截止时间：AT_TIME 为用户指定，AFTER_HOURS 为创建时折算；NONE/AT_COMPLETE 恒为空
    expires_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 预留账单扩展（MVP 不启用）
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
