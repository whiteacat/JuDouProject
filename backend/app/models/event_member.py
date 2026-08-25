"""组队成员模型。"""

from __future__ import annotations

import datetime as dt
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventMemberStatus:
    JOINED = "JOINED"
    LEFT = "LEFT"


class EventMember(Base):
    __tablename__ = "event_members"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_members_event_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String(16), default=EventMemberStatus.JOINED)
    # 成员可参加时间窗口：可跨多天、每天多段。
    # 结构：[{"date": "YYYY-MM-DD", "start": "HH:mm", "end": "HH:mm"}, ...]
    time_windows: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=sa.text("'[]'::jsonb")
    )
    joined_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
