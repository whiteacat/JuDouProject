"""评价模型。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    DateTime,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_reviews_event_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    overall_score: Mapped[float] = mapped_column(Numeric(2, 1))
    taste_score: Mapped[float] = mapped_column(Numeric(2, 1))
    value_score: Mapped[float] = mapped_column(Numeric(2, 1))
    environment_score: Mapped[float] = mapped_column(Numeric(2, 1))
    service_score: Mapped[float] = mapped_column(Numeric(2, 1))
    traffic_score: Mapped[float] = mapped_column(Numeric(2, 1))
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
