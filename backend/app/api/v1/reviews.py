"""评价与群组餐厅库路由。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.restaurant import RestaurantOut
from app.schemas.review import (
    GroupRestaurantOut,
    GroupStats,
    ReviewCreate,
    ReviewOut,
)
from app.services import group_restaurant_service, review_service

router = APIRouter(tags=["reviews", "group-restaurants"])


@router.post(
    "/events/{event_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_review(
    event_id: int,
    body: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewOut:
    review = await review_service.submit_review(
        db, event_id, current_user.id, body.model_dump()
    )
    return ReviewOut(
        id=review.id,
        user_id=current_user.id,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        overall_score=float(review.overall_score),
        taste_score=float(review.taste_score),
        value_score=float(review.value_score),
        environment_score=float(review.environment_score),
        service_score=float(review.service_score),
        traffic_score=float(review.traffic_score),
        content=review.content,
        created_at=review.created_at,
    )


@router.get("/restaurants/{restaurant_id}/reviews", response_model=list[ReviewOut])
async def list_restaurant_reviews(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewOut]:
    reviews = await review_service.list_restaurant_reviews(
        db, restaurant_id, current_user.id
    )
    return [ReviewOut(**r) for r in reviews]


@router.get("/groups/{group_id}/restaurants", response_model=list[GroupRestaurantOut])
async def list_group_restaurants(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupRestaurantOut]:
    items = await group_restaurant_service.list_group_restaurants(
        db, group_id, current_user.id
    )
    return [
        GroupRestaurantOut(
            restaurant=RestaurantOut.model_validate(item["restaurant"]),
            group_stats=GroupStats(**item["group_stats"]),
        )
        for item in items
    ]


@router.get(
    "/groups/{group_id}/restaurants/{restaurant_id}",
    response_model=GroupRestaurantOut,
)
async def get_group_restaurant(
    group_id: int,
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupRestaurantOut:
    item = await group_restaurant_service.get_group_restaurant(
        db, group_id, restaurant_id, current_user.id
    )
    return GroupRestaurantOut(
        restaurant=RestaurantOut.model_validate(item["restaurant"]),
        group_stats=GroupStats(**item["group_stats"]),
    )


@router.get(
    "/groups/{group_id}/restaurants/{restaurant_id}/reviews",
    response_model=list[ReviewOut],
)
async def list_group_restaurant_reviews(
    group_id: int,
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewOut]:
    reviews = await review_service.list_group_restaurant_reviews(
        db, group_id, restaurant_id, current_user.id
    )
    return [ReviewOut(**r) for r in reviews]
