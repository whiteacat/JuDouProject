"""群公告模型：每个群组一条最新公告（群主维护）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (UniqueConstraint("group_id", name="uq_announcement_group"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    content: Mapped[str] = mapped_column(Text)
    # 最后发布公告的群主用户 ID
    owner_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
