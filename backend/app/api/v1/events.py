"""组队事件路由。"""

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import EventCreate, EventMemberOut, EventOut
from app.services import event_service

router = APIRouter(tags=["events"])


@router.post(
    "/groups/{group_id}/events",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_group_event(
    group_id: int,
    body: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    event = await event_service.create_event(
        db, group_id, current_user.id, body.model_dump()
    )
    detail = await event_service.get_event_detail(db, event.id, current_user.id)
    return EventOut(**detail)


@router.get("/groups/{group_id}/events", response_model=list[EventOut])
async def list_group_events(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventOut]:
    events = await event_service.list_group_events(db, group_id, current_user.id)
    return [EventOut(**e) for e in events]


@router.get("/groups/{group_id}/events/map", response_model=list[EventOut])
async def map_group_events(
    group_id: int,
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    radius: int = Query(default=3000, ge=100, le=50000),
    event_status: Optional[str] = Query(None, max_length=16),
    start_time: Optional[dt.datetime] = Query(None),
    end_time: Optional[dt.datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventOut]:
    events = await event_service.map_events(
        db,
        group_id,
        current_user.id,
        longitude,
        latitude,
        radius,
        event_status,
        start_time,
        end_time,
    )
    return [EventOut(**e) for e in events]


# 注意：/events/mine 必须注册在 /events/{event_id} 之前，否则 "mine" 会被解析为 event_id
@router.get("/events/mine", response_model=list[EventOut])
async def get_my_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventOut]:
    events = await event_service.list_my_events(db, current_user.id)
    return [EventOut(**e) for e in events]


@router.get("/events/{event_id}", response_model=EventOut)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    detail = await event_service.get_event_detail(db, event_id, current_user.id)
    return EventOut(**detail)


@router.get("/events/{event_id}/members", response_model=list[EventMemberOut])
async def get_event_members(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventMemberOut]:
    members = await event_service.list_members(db, event_id, current_user.id)
    return [EventMemberOut(**m) for m in members]


@router.post("/events/{event_id}/join", response_model=EventOut)
async def join_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    event = await event_service.join_event(db, event_id, current_user.id)
    detail = await event_service.get_event_detail(db, event.id, current_user.id)
    return EventOut(**detail)


@router.post("/events/{event_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await event_service.leave_event(db, event_id, current_user.id)


@router.post("/events/{event_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await event_service.complete_event(db, event_id, current_user.id)


@router.post("/events/{event_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await event_service.cancel_event(db, event_id, current_user.id)
