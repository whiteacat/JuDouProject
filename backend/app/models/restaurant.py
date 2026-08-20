"""餐厅模型。"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Restaurant(Base):
    __tablename__ = "restaurants"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_restaurants_source_source_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    brand: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(String(256), default="")
    longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    # PostGIS 空间点（SRID 4326），带 GIST 索引，用于距离查询
    location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avg_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    business_hours: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="amap")
    source_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
