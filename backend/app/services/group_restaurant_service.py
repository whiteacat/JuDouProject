"""群组餐厅库业务逻辑。"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventStatus, GroupEvent
from app.models.group_restaurant import GroupRestaurant
from app.models.restaurant import Restaurant
from app.models.review import Review
from app.services import group_service

RESTAURANT_NOT_FOUND = "餐厅不存在"


async def record_visit(
    db: AsyncSession,
    group_id: int,
    restaurant_id: int,
    visited_at: Optional[dt.datetime] = None,
) -> None:
    """事件完成时将餐厅记入群组餐厅库（visit_count+1、last_visit_at 更新）。"""
    result = await db.execute(
        select(GroupRestaurant).where(
            GroupRestaurant.group_id == group_id,
            GroupRestaurant.restaurant_id == restaurant_id,
        )
    )
    gr = result.scalar_one_or_none()
    now = visited_at or dt.datetime.now(dt.timezone.utc)
    if gr is None:
        db.add(
            GroupRestaurant(
                group_id=group_id,
                restaurant_id=restaurant_id,
                visit_count=1,
                last_visit_at=now,
            )
        )
    else:
        gr.visit_count += 1
        gr.last_visit_at = now


async def recompute_scores(
    db: AsyncSession, group_id: int, restaurant_id: int
) -> GroupRestaurant:
    """按该群对该餐厅的全部评价重算聚合分（§12 简单平均），不存在则创建记录。

    visit_count 按"该群已完成组队数"重算：兼容旧事件完成时未入库、
    由评价首次触发建记录的场景（避免出现"去过 0 次"的错误数据）。
    """
    result = await db.execute(
        select(
            func.avg(Review.overall_score),
            func.avg(Review.taste_score),
            func.avg(Review.value_score),
            func.avg(Review.environment_score),
            func.avg(Review.service_score),
            func.avg(Review.traffic_score),
        ).where(
            Review.group_id == group_id,
            Review.restaurant_id == restaurant_id,
        )
    )
    (overall, taste, value, env, service, traffic) = result.one()

    def _r(v) -> Optional[float]:
        return round(float(v), 1) if v is not None else None

    visit = await db.execute(
        select(func.count(GroupEvent.id)).where(
            GroupEvent.group_id == group_id,
            GroupEvent.restaurant_id == restaurant_id,
            GroupEvent.status == EventStatus.COMPLETED,
        )
    )
    visit_count = int(visit.scalar() or 0)

    gr_result = await db.execute(
        select(GroupRestaurant).where(
            GroupRestaurant.group_id == group_id,
            GroupRestaurant.restaurant_id == restaurant_id,
        )
    )
    gr = gr_result.scalar_one_or_none()
    if gr is None:
        gr = GroupRestaurant(group_id=group_id, restaurant_id=restaurant_id)
        db.add(gr)
    gr.visit_count = visit_count
    gr.group_score = _r(overall)
    gr.taste_score = _r(taste)
    gr.value_score = _r(value)
    gr.environment_score = _r(env)
    gr.service_score = _r(service)
    gr.traffic_score = _r(traffic)
    return gr


def _group_stats(gr: GroupRestaurant) -> dict:
    return {
        "visit_count": gr.visit_count,
        "score": float(gr.group_score) if gr.group_score is not None else None,
        "taste": float(gr.taste_score) if gr.taste_score is not None else None,
        "value": float(gr.value_score) if gr.value_score is not None else None,
        "environment": float(gr.environment_score) if gr.environment_score is not None else None,
        "service": float(gr.service_score) if gr.service_score is not None else None,
        "traffic": float(gr.traffic_score) if gr.traffic_score is not None else None,
    }


async def list_group_restaurants(
    db: AsyncSession, group_id: int, user_id: int
) -> list[dict]:
    """群组餐厅库列表（含访问次数与聚合评分）。"""
    await group_service.get_group_detail(db, group_id, user_id)  # 群成员校验
    result = await db.execute(
        select(GroupRestaurant, Restaurant)
        .join(Restaurant, Restaurant.id == GroupRestaurant.restaurant_id)
        .where(GroupRestaurant.group_id == group_id, Restaurant.status == 1)
        .order_by(GroupRestaurant.visit_count.desc(), GroupRestaurant.updated_at.desc())
    )
    return [
        {"restaurant": restaurant, "group_stats": _group_stats(gr)}
        for gr, restaurant in result.all()
    ]


async def get_group_restaurant(
    db: AsyncSession, group_id: int, restaurant_id: int, user_id: int
) -> dict:
    """群内某餐厅详情：餐厅信息 + 群聚合评分（未去过则返回空统计）。"""
    await group_service.get_group_detail(db, group_id, user_id)
    restaurant = await db.get(Restaurant, restaurant_id)
    if restaurant is None or restaurant.status != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=RESTAURANT_NOT_FOUND
        )

    result = await db.execute(
        select(GroupRestaurant).where(
            GroupRestaurant.group_id == group_id,
            GroupRestaurant.restaurant_id == restaurant_id,
        )
    )
    gr = result.scalar_one_or_none()
    if gr is None:
        # 未入群餐厅库：返回空统计（不落库；default 只在 flush 时生效，需显式给 visit_count）
        gr = GroupRestaurant(
            group_id=group_id, restaurant_id=restaurant_id, visit_count=0
        )
    return {"restaurant": restaurant, "group_stats": _group_stats(gr)}
