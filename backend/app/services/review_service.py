"""评价业务逻辑。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventStatus, GroupEvent
from app.models.event_member import EventMember, EventMemberStatus
from app.models.group import Group
from app.models.restaurant import Restaurant
from app.models.review import Review
from app.models.user import User
from app.services import group_restaurant_service, group_service
from app.services.event_service import _get_event

ALREADY_REVIEWED = "该聚餐已评价过"
NOT_ELIGIBLE = "仅参与聚餐的成员可评价"


async def submit_review(
    db: AsyncSession, event_id: int, user_id: int, payload: dict
) -> Review:
    event = await _get_event(db, event_id, user_id)
    if event.status != EventStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="组队完成后才能评价"
        )
    if event.restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="该组队未指定餐厅，无法评价"
        )

    # 评价资格：仅 JOINED 成员（§28）
    membership = await db.execute(
        select(EventMember).where(
            EventMember.event_id == event_id,
            EventMember.user_id == user_id,
        )
    )
    member = membership.scalar_one_or_none()
    if member is None or member.status != EventMemberStatus.JOINED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NOT_ELIGIBLE)

    # 一次聚餐只能评价一次（UNIQUE(event_id, user_id) 兜底）
    existing = await db.execute(
        select(Review.id).where(Review.event_id == event_id, Review.user_id == user_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_REVIEWED)

    review = Review(
        restaurant_id=event.restaurant_id,
        group_id=event.group_id,
        event_id=event_id,
        user_id=user_id,
        overall_score=payload["overall_score"],
        taste_score=payload["taste_score"],
        value_score=payload["value_score"],
        environment_score=payload["environment_score"],
        service_score=payload["service_score"],
        traffic_score=payload["traffic_score"],
        content=payload.get("content") or "",
    )
    db.add(review)
    # 事务内重算群组聚合评分
    await group_restaurant_service.recompute_scores(
        db, event.group_id, event.restaurant_id
    )
    await db.commit()
    await db.refresh(review)
    return review


async def list_restaurant_reviews(
    db: AsyncSession, restaurant_id: int, user_id: int
) -> list[dict]:
    """某餐厅的全部评价（任何登录用户可看）。"""
    result = await db.execute(
        select(Review)
        .where(Review.restaurant_id == restaurant_id)
        .order_by(Review.created_at.desc())
    )
    return await _with_users(db, result.scalars().all())


async def list_group_restaurant_reviews(
    db: AsyncSession, group_id: int, restaurant_id: int, user_id: int
) -> list[dict]:
    """某群对某餐厅的评价（群成员可看）。"""
    await group_service.get_group_detail(db, group_id, user_id)  # 群成员校验
    result = await db.execute(
        select(Review)
        .where(Review.group_id == group_id, Review.restaurant_id == restaurant_id)
        .order_by(Review.created_at.desc())
    )
    return await _with_users(db, result.scalars().all())


async def list_my_reviews(db: AsyncSession, user_id: int) -> list[dict]:
    """当前用户的全部评价，附餐厅/群/组队信息。"""
    result = await db.execute(
        select(Review, Restaurant.name, Group.name, GroupEvent.title)
        .join(Restaurant, Restaurant.id == Review.restaurant_id)
        .outerjoin(Group, Group.id == Review.group_id)
        .outerjoin(GroupEvent, GroupEvent.id == Review.event_id)
        .where(Review.user_id == user_id)
        .order_by(Review.created_at.desc())
    )
    return [
        {
            "id": review.id,
            "restaurant_id": review.restaurant_id,
            "restaurant_name": restaurant_name or "",
            "group_id": review.group_id,
            "group_name": group_name,
            "event_id": review.event_id,
            "event_title": event_title,
            "overall_score": float(review.overall_score),
            "content": review.content,
            "created_at": review.created_at,
        }
        for review, restaurant_name, group_name, event_title in result.all()
    ]


async def _with_users(db: AsyncSession, reviews: list[Review]) -> list[dict]:
    if not reviews:
        return []
    user_ids = {r.user_id for r in reviews}
    users = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map = {u.id: u for u in users.scalars().all()}
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "nickname": user_map[r.user_id].nickname if r.user_id in user_map else "",
            "avatar_url": user_map[r.user_id].avatar_url if r.user_id in user_map else "",
            "overall_score": float(r.overall_score),
            "taste_score": float(r.taste_score),
            "value_score": float(r.value_score),
            "environment_score": float(r.environment_score),
            "service_score": float(r.service_score),
            "traffic_score": float(r.traffic_score),
            "content": r.content,
            "created_at": r.created_at,
        }
        for r in reviews
    ]
