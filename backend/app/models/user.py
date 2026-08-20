"""用户模型。"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    unionid: Mapped[Optional[str]] = mapped_column(  # noqa: UP045 - py3.9 下 SQLAlchemy 无法解析 str | None
        String(128), nullable=True
    )
    nickname: Mapped[str] = mapped_column(String(64), default="微信用户")
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
