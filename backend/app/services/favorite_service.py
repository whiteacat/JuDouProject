"""收藏业务逻辑。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import GroupEvent
from app.models.favorite import Favorite


async def is_favorite(db: AsyncSession, user_id: int, event_id: int) -> bool:
    result = await db.execute(
        select(Favorite.id).where(Favorite.user_id == user_id, Favorite.event_id == event_id)
    )
    return result.scalar_one_or_none() is not None


async def add_favorite(db: AsyncSession, user_id: int, event_id: int) -> None:
    """收藏活动；已收藏则幂等返回。

    Raises:
        HTTPException: 活动不存在时 404。
    """
    event = await db.get(GroupEvent, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")

    existing = await db.execute(
        select(Favorite.id).where(Favorite.user_id == user_id, Favorite.event_id == event_id)
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(Favorite(user_id=user_id, event_id=event_id))
    await db.commit()


async def remove_favorite(db: AsyncSession, user_id: int, event_id: int) -> None:
    """取消收藏；未收藏则幂等返回。"""
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.event_id == event_id)
    )
    fav = result.scalar_one_or_none()
    if fav is None:
        return
    await db.delete(fav)
    await db.commit()


async def list_favorites(db: AsyncSession, user_id: int) -> list[GroupEvent]:
    """我的收藏活动列表（按收藏时间倒序）。"""
    result = await db.execute(
        select(GroupEvent)
        .join(Favorite, Favorite.event_id == GroupEvent.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    return list(result.scalars().all())
