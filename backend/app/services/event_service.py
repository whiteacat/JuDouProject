"""组队事件业务逻辑。"""

from __future__ import annotations

import datetime as dt
import math
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventStatus, GroupEvent
from app.models.event_member import EventMember, EventMemberStatus
from app.models.member import GroupMember
from app.models.restaurant import Restaurant
from app.models.user import User
from app.services import group_restaurant_service

EVENT_NOT_FOUND = "组队不存在或无权访问"
GROUP_MEMBER_REQUIRED = "仅群组成员可操作"


def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """平面距离近似（米）：半径 5km 内足够精确，未来可换 PostGIS ST_DWithin。"""
    dlat = (lat2 - lat1) * 111320.0
    dlon = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


async def get_event_membership(
    db: AsyncSession, event_id: int, user_id: int
) -> Optional[EventMember]:
    result = await db.execute(
        select(EventMember).where(
            EventMember.event_id == event_id,
            EventMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def count_active_members(db: AsyncSession, event_id: int) -> int:
    result = await db.execute(
        select(func.count(EventMember.id)).where(
            EventMember.event_id == event_id,
            EventMember.status == EventMemberStatus.JOINED,
        )
    )
    return int(result.scalar() or 0)


async def _count_batch(db: AsyncSession, event_ids: list[int]) -> dict[int, int]:
    if not event_ids:
        return {}
    result = await db.execute(
        select(EventMember.event_id, func.count(EventMember.id))
        .where(
            EventMember.event_id.in_(event_ids),
            EventMember.status == EventMemberStatus.JOINED,
        )
        .group_by(EventMember.event_id)
    )
    return {event_id: int(count) for event_id, count in result.all()}


async def _require_group_member(
    db: AsyncSession, group_id: int, user_id: int
) -> GroupMember:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.status == 1,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=GROUP_MEMBER_REQUIRED
        )
    return member


async def _get_event(
    db: AsyncSession, event_id: int, user_id: int, *, for_update: bool = False
) -> GroupEvent:
    """取事件并校验当前用户是该组队所属群的成员（非成员视为无权访问）。"""
    stmt = select(GroupEvent).where(GroupEvent.id == event_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND)

    member = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == event.group_id,
            GroupMember.user_id == user_id,
            GroupMember.status == 1,
        )
    )
    if member.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND)
    return event


def _restaurant_brief(restaurant: Restaurant) -> dict:
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "longitude": float(restaurant.longitude),
        "latitude": float(restaurant.latitude),
    }


def _event_dict(event: GroupEvent, current_members: int, restaurant: Optional[Restaurant]) -> dict:
    return {
        "id": event.id,
        "group_id": event.group_id,
        "creator_id": event.creator_id,
        "title": event.title,
        "event_time": event.event_time,
        "status": event.status,
        "min_members": event.min_members,
        "max_members": event.max_members,
        "current_members": current_members,
        "remark": event.remark,
        "latitude": float(event.latitude) if event.latitude is not None else None,
        "longitude": float(event.longitude) if event.longitude is not None else None,
        "restaurant": _restaurant_brief(restaurant) if restaurant else None,
    }


async def create_event(
    db: AsyncSession, group_id: int, user_id: int, payload: dict
) -> GroupEvent:
    await _require_group_member(db, group_id, user_id)

    event_time = payload["event_time"]
    if event_time <= dt.datetime.now(dt.timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="组队时间必须晚于当前时间"
        )
    min_members = payload.get("min_members", 1)
    max_members = payload["max_members"]
    if max_members < 1 or min_members < 1 or min_members > max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="人数设置不合法"
        )

    restaurant_id = payload.get("restaurant_id")
    restaurant = None
    if restaurant_id is not None:
        restaurant = await db.get(Restaurant, restaurant_id)
        if restaurant is None or restaurant.status != 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="餐厅不存在"
            )

    latitude = longitude = None
    if restaurant is not None:
        latitude = float(restaurant.latitude)
        longitude = float(restaurant.longitude)
    elif payload.get("latitude") is not None and payload.get("longitude") is not None:
        latitude = payload["latitude"]
        longitude = payload["longitude"]

    event = GroupEvent(
        group_id=group_id,
        creator_id=user_id,
        restaurant_id=restaurant_id,
        title=payload["title"],
        event_time=event_time,
        min_members=min_members,
        max_members=max_members,
        latitude=latitude,
        longitude=longitude,
        remark=payload.get("remark"),
        status=EventStatus.RECRUITING,
    )
    db.add(event)
    await db.flush()
    # 创建者自动成为第一名成员
    db.add(
        EventMember(
            event_id=event.id, user_id=user_id, status=EventMemberStatus.JOINED
        )
    )
    await db.commit()
    await db.refresh(event)
    return event


async def map_events(
    db: AsyncSession,
    group_id: int,
    user_id: int,
    longitude: Optional[float] = None,
    latitude: Optional[float] = None,
    radius: Optional[int] = None,
    event_status: Optional[str] = None,
    start_time: Optional[dt.datetime] = None,
    end_time: Optional[dt.datetime] = None,
) -> list[dict]:
    await _require_group_member(db, group_id, user_id)

    stmt = select(GroupEvent).where(GroupEvent.group_id == group_id)
    if event_status:
        stmt = stmt.where(GroupEvent.status == event_status)
    if start_time:
        stmt = stmt.where(GroupEvent.event_time >= start_time)
    if end_time:
        stmt = stmt.where(GroupEvent.event_time <= end_time)
    result = await db.execute(stmt.order_by(GroupEvent.event_time.asc()))
    events = list(result.scalars().all())

    # 坐标过滤（MVP 平面近似；未来换 PostGIS ST_DWithin）
    filtered = []
    for event in events:
        if event.latitude is None or event.longitude is None:
            continue
        if (
            radius
            and longitude is not None
            and latitude is not None
            and _distance(
                latitude, longitude, float(event.latitude), float(event.longitude)
            )
            > radius
        ):
            continue
        filtered.append(event)

    counts = await _count_batch(db, [e.id for e in filtered])
    restaurant_ids = {e.restaurant_id for e in filtered if e.restaurant_id}
    restaurants: dict[int, Restaurant] = {}
    if restaurant_ids:
        r_result = await db.execute(
            select(Restaurant).where(Restaurant.id.in_(restaurant_ids))
        )
        restaurants = {r.id: r for r in r_result.scalars().all()}

    return [
        _event_dict(e, counts.get(e.id, 0), restaurants.get(e.restaurant_id))
        for e in filtered
    ]


async def list_group_events(
    db: AsyncSession, group_id: int, user_id: int
) -> list[dict]:
    """群内组队列表：成员可见、含全部状态、按时间倒序、无坐标过滤。"""
    await _require_group_member(db, group_id, user_id)

    result = await db.execute(
        select(GroupEvent)
        .where(GroupEvent.group_id == group_id)
        .order_by(GroupEvent.event_time.desc())
    )
    events = list(result.scalars().all())

    counts = await _count_batch(db, [e.id for e in events])
    restaurant_ids = {e.restaurant_id for e in events if e.restaurant_id}
    restaurants: dict[int, Restaurant] = {}
    if restaurant_ids:
        r_result = await db.execute(
            select(Restaurant).where(Restaurant.id.in_(restaurant_ids))
        )
        restaurants = {r.id: r for r in r_result.scalars().all()}

    return [
        _event_dict(e, counts.get(e.id, 0), restaurants.get(e.restaurant_id))
        for e in events
    ]


async def join_event(db: AsyncSession, event_id: int, user_id: int) -> GroupEvent:
    """加入组队：行锁串行化并发加入，保证不超员。"""
    event = await _get_event(db, event_id, user_id, for_update=True)
    if event.status not in (EventStatus.RECRUITING, EventStatus.CONFIRMED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态不可加入"
        )
    if event.event_time <= dt.datetime.now(dt.timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="组队时间已过，无法加入"
        )

    membership = await get_event_membership(db, event_id, user_id)
    if membership is not None and membership.status == EventMemberStatus.JOINED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="已在组队中"
        )

    current = await count_active_members(db, event_id)
    if current >= event.max_members:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="组队人数已满")

    if membership is None:
        db.add(
            EventMember(
                event_id=event_id, user_id=user_id, status=EventMemberStatus.JOINED
            )
        )
    else:
        membership.status = EventMemberStatus.JOINED

    if current + 1 >= event.max_members:
        event.status = EventStatus.CONFIRMED  # 满员自动确认
    await db.commit()
    await db.refresh(event)
    return event


async def leave_event(db: AsyncSession, event_id: int, user_id: int) -> None:
    event = await _get_event(db, event_id, user_id, for_update=True)
    if event.status not in (EventStatus.RECRUITING, EventStatus.CONFIRMED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态不可退出"
        )

    membership = await get_event_membership(db, event_id, user_id)
    if membership is None or membership.status != EventMemberStatus.JOINED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="未加入该组队"
        )

    membership.status = EventMemberStatus.LEFT
    if event.status == EventStatus.CONFIRMED:
        event.status = EventStatus.RECRUITING  # 有人退出则回到招募中，允许他人加入
    await db.commit()


async def complete_event(db: AsyncSession, event_id: int, user_id: int) -> None:
    event = await _get_event(db, event_id, user_id, for_update=True)
    if event.creator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅创建者可操作"
        )
    if event.status not in (EventStatus.RECRUITING, EventStatus.CONFIRMED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态不可完成"
        )
    event.status = EventStatus.COMPLETED
    event.completed_at = dt.datetime.now(dt.timezone.utc)
    if event.restaurant_id:
        # 聚餐完成：餐厅自动进入群组餐厅库（visit_count+1）
        await group_restaurant_service.record_visit(
            db, event.group_id, event.restaurant_id, event.completed_at
        )
    await db.commit()


async def cancel_event(db: AsyncSession, event_id: int, user_id: int) -> None:
    event = await _get_event(db, event_id, user_id, for_update=True)
    if event.creator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅创建者可操作"
        )
    if event.status not in (EventStatus.RECRUITING, EventStatus.CONFIRMED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态不可取消"
        )
    event.status = EventStatus.CANCELLED
    await db.commit()


async def list_my_events(db: AsyncSession, user_id: int) -> list[dict]:
    """当前用户创建或已加入的组队（创建者自动入队，故 JOINED 即覆盖两种情况）。"""
    result = await db.execute(
        select(GroupEvent)
        .join(EventMember, EventMember.event_id == GroupEvent.id)
        .where(
            EventMember.user_id == user_id,
            EventMember.status == EventMemberStatus.JOINED,
        )
        .order_by(GroupEvent.event_time.desc())
    )
    events = list(result.scalars().all())

    counts = await _count_batch(db, [e.id for e in events])
    restaurant_ids = {e.restaurant_id for e in events if e.restaurant_id}
    restaurants: dict[int, Restaurant] = {}
    if restaurant_ids:
        r_result = await db.execute(
            select(Restaurant).where(Restaurant.id.in_(restaurant_ids))
        )
        restaurants = {r.id: r for r in r_result.scalars().all()}

    return [
        _event_dict(e, counts.get(e.id, 0), restaurants.get(e.restaurant_id))
        for e in events
    ]


async def get_event_detail(db: AsyncSession, event_id: int, user_id: int) -> dict:
    event = await _get_event(db, event_id, user_id)
    current = await count_active_members(db, event_id)
    restaurant = None
    if event.restaurant_id:
        restaurant = await db.get(Restaurant, event.restaurant_id)
    return _event_dict(event, current, restaurant)


async def list_members(db: AsyncSession, event_id: int, user_id: int) -> list[dict]:
    await _get_event(db, event_id, user_id)
    result = await db.execute(
        select(EventMember)
        .where(
            EventMember.event_id == event_id,
            EventMember.status == EventMemberStatus.JOINED,
        )
        .order_by(EventMember.joined_at.asc())
    )
    members = result.scalars().all()
    user_ids = [m.user_id for m in members]
    users = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map = {u.id: u for u in users.scalars().all()}
    return [
        {
            "user_id": m.user_id,
            "joined_at": m.joined_at,
            "nickname": user_map[m.user_id].nickname if m.user_id in user_map else "",
            "avatar_url": user_map[m.user_id].avatar_url if m.user_id in user_map else "",
        }
        for m in members
    ]
