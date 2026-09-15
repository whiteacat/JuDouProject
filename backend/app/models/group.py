"""群组模型。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    # 封面背景图：preset://group_cover/NN 白名单（不允许上传），None 用默认背景
    cover_url: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[int] = mapped_column(BigInteger)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
