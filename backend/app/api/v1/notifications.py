"""站内通知路由：列表 / 未读数 / 单条已读 / 全部已读。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationOut, UnreadCountOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=dict)
async def list_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """我的通知列表（时间倒序，分页）。"""
    offset = (page - 1) * size
    items_result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    items = items_result.scalars().all()
    total_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id
        )
    )
    return {
        "items": [NotificationOut.model_validate(n) for n in items],
        "total": int(total_result.scalar_one()),
    }


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountOut:
    """未读通知数（角标用）。"""
    count = await notification_service.unread_count(db, current_user.id)
    return UnreadCountOut(count=count)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """单条标记已读（幂等；非本人通知 404）。"""
    found = await notification_service.mark_read(db, current_user.id, notification_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在"
        )
    await db.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """全部标记已读。"""
    await notification_service.mark_all_read(db, current_user.id)
    await db.commit()
