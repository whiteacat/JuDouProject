"""用户反馈模型：帮助与反馈页提交的问题/建议。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # 反馈内容
    content: Mapped[str] = mapped_column(Text)
    # 联系方式（选填，便于回访）
    contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 反馈类型：bug / suggestion / other
    kind: Mapped[str] = mapped_column(String(16), default="other")
    # 是否已处理（管理端标记，预留）
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
