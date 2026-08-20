"""用户路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.event_member import EventMember, EventMemberStatus
from app.models.member import GroupMember
from app.models.review import Review
from app.models.user import User
from app.schemas.review import MyReviewOut
from app.schemas.user import UserOut, UserStatsOut
from app.services import review_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/stats", response_model=UserStatsOut)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserStatsOut:
    group_count = (
        await db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.user_id == current_user.id,
                GroupMember.status == 1,
            )
        )
    ).scalar() or 0
    event_count = (
        await db.execute(
            select(func.count(EventMember.id)).where(
                EventMember.user_id == current_user.id,
                EventMember.status == EventMemberStatus.JOINED,
            )
        )
    ).scalar() or 0
    review_count = (
        await db.execute(
            select(func.count(Review.id)).where(Review.user_id == current_user.id)
        )
    ).scalar() or 0
    return UserStatsOut(
        group_count=int(group_count),
        event_count=int(event_count),
        review_count=int(review_count),
    )


@router.get("/me/reviews", response_model=list[MyReviewOut])
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyReviewOut]:
    reviews = await review_service.list_my_reviews(db, current_user.id)
    return [MyReviewOut(**r) for r in reviews]
