"""群组餐厅库模型：某个群对某个餐厅的聚合认知。"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GroupRestaurant(Base):
    __tablename__ = "group_restaurants"
    __table_args__ = (
        UniqueConstraint(
            "group_id", "restaurant_id", name="uq_group_restaurants_group_restaurant"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    restaurant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_visit_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    group_score: Mapped[Optional[float]] = mapped_column(Numeric(2, 1), nullable=True)
    taste_score: Mapped[Optional[float]] = mapped_column(Numeric(2, 1), nullable=True)
    value_score: Mapped[Optional[float]] = mapped_column(Numeric(2, 1), nullable=True)
    environment_score: Mapped[Optional[float]] = mapped_column(
        Numeric(2, 1), nullable=True
    )
    service_score: Mapped[Optional[float]] = mapped_column(
        Numeric(2, 1), nullable=True
    )
    traffic_score: Mapped[Optional[float]] = mapped_column(
        Numeric(2, 1), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
