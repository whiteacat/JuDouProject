"""餐厅业务逻辑。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant
from app.services.amap import AmapClient

RESTAURANT_NOT_FOUND = "餐厅不存在"


def _location_wkt(longitude: float, latitude: float) -> str:
    return f"SRID=4326;POINT({longitude} {latitude})"


def _truncate(value, limit: int) -> str | None:
    """截断超长字符串，避免真实数据源字段超限导致写库失败。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


async def upsert_from_poi(db: AsyncSession, poi: dict) -> Restaurant:
    """按 source+source_id 查找；存在则更新可变信息，否则创建。"""
    result = await db.execute(
        select(Restaurant).where(
            Restaurant.source == "amap",
            Restaurant.source_id == poi["source_id"],
        )
    )
    restaurant = result.scalar_one_or_none()

    if restaurant is None:
        restaurant = Restaurant(
            source="amap",
            source_id=_truncate(poi["source_id"], 64) or "",
            name=_truncate(poi["name"], 128) or "",
            category=_truncate(poi.get("category"), 64) or "",
            address=_truncate(poi.get("address"), 256) or "",
            longitude=poi["longitude"],
            latitude=poi["latitude"],
            phone=_truncate(poi.get("phone"), 128),
            brand=_truncate(poi.get("brand"), 64),
            avg_price=poi.get("avg_price"),
            cover_url=_truncate(poi.get("cover_url"), 512),
            business_hours=poi.get("business_hours"),
        )
        db.add(restaurant)
    else:
        restaurant.name = _truncate(poi["name"], 128) or restaurant.name
        restaurant.category = _truncate(poi.get("category"), 64) or restaurant.category
        restaurant.address = _truncate(poi.get("address"), 256) or restaurant.address
        restaurant.longitude = poi["longitude"]
        restaurant.latitude = poi["latitude"]
        phone = _truncate(poi.get("phone"), 128)
        if phone:
            restaurant.phone = phone

    restaurant.location = _location_wkt(poi["longitude"], poi["latitude"])
    await db.commit()
    await db.refresh(restaurant)
    return restaurant


async def search_restaurants(
    db: AsyncSession,
    keyword: str,
    longitude: float,
    latitude: float,
    radius: int = 3000,
    category: str = "",
) -> list[Restaurant]:
    """搜索 POI 并落库（复用已有记录），返回标准化餐厅列表。"""
    pois = await AmapClient().search_poi(keyword, longitude, latitude, radius, category)
    results = []
    for poi in pois:
        if not poi["source_id"]:
            continue
        results.append(await upsert_from_poi(db, poi))
    return results


async def get_restaurant(db: AsyncSession, restaurant_id: int) -> Restaurant:
    restaurant = await db.get(Restaurant, restaurant_id)
    if restaurant is None or restaurant.status != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=RESTAURANT_NOT_FOUND
        )
    return restaurant
