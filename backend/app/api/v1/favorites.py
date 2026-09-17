"""收藏路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.favorite import FavoriteItemOut, FavoriteStatusOut
from app.services import favorite_service

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteItemOut])
async def list_my_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FavoriteItemOut]:
    """我的收藏列表（含活动摘要，按收藏时间倒序）。"""
    events = await favorite_service.list_favorites(db, current_user.id)
    out: list[FavoriteItemOut] = []
    for ev in events:
        restaurant_name: str | None = None
        if ev.restaurant_id is not None:
            restaurant = await db.get(Restaurant, ev.restaurant_id)
            if restaurant is not None:
                restaurant_name = restaurant.name
        fav_created = (
            await db.execute(
                select(Favorite.created_at).where(
                    Favorite.user_id == current_user.id, Favorite.event_id == ev.id
                )
            )
        ).scalar_one_or_none()
        out.append(
            FavoriteItemOut(
                id=ev.id,
                group_id=ev.group_id,
                title=ev.title,
                cover_url=ev.cover_url,
                budget=float(ev.budget) if ev.budget is not None else None,
                event_time=ev.event_time,
                status=ev.status,
                current_members=0,
                max_members=ev.max_members,
                restaurant_name=restaurant_name,
                favorited_at=fav_created,
            )
        )
    return out


@router.get("/{event_id}", response_model=FavoriteStatusOut)
async def get_favorite_status(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FavoriteStatusOut:
    """查询某活动是否已收藏。"""
    favorited = await favorite_service.is_favorite(db, current_user.id, event_id)
    return FavoriteStatusOut(favorited=favorited)


@router.put("/{event_id}", response_model=FavoriteStatusOut)
async def add_favorite(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FavoriteStatusOut:
    """收藏活动（幂等）。"""
    await favorite_service.add_favorite(db, current_user.id, event_id)
    return FavoriteStatusOut(favorited=True)


@router.delete("/{event_id}", response_model=FavoriteStatusOut)
async def remove_favorite(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FavoriteStatusOut:
    """取消收藏（幂等）。"""
    await favorite_service.remove_favorite(db, current_user.id, event_id)
    return FavoriteStatusOut(favorited=False)
