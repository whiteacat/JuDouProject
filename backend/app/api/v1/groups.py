"""群组路由。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupOut,
    JoinByCodeRequest,
    MemberOut,
    TransferRequest,
)
from app.services import group_service

router = APIRouter(prefix="/groups", tags=["groups"])


def _group_to_out(group, member_count: int) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        avatar_url=group.avatar_url,
        owner_id=group.owner_id,
        invite_code=group.invite_code,
        member_count=member_count,
        created_at=group.created_at,
    )


async def _group_out_with_count(db: AsyncSession, group) -> GroupOut:
    counts = await group_service.count_active_members_batch(db, [group.id])
    return _group_to_out(group, counts.get(group.id, 1))


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupOut:
    group = await group_service.create_group(db, current_user.id, body.name, body.avatar_url)
    return await _group_out_with_count(db, group)


@router.get("", response_model=list[GroupOut])
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupOut]:
    groups = await group_service.list_my_groups(db, current_user.id)
    counts = await group_service.count_active_members_batch(
        db, [g.id for g in groups]
    )
    return [_group_to_out(g, counts.get(g.id, 1)) for g in groups]


@router.post("/join-by-code", response_model=GroupOut)
async def join_by_code(
    body: JoinByCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupOut:
    group = await group_service.join_by_code(db, current_user.id, body.invite_code)
    return await _group_out_with_count(db, group)


@router.get("/{group_id}", response_model=GroupOut)
async def get_group_detail(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupOut:
    group = await group_service.get_group_detail(db, group_id, current_user.id)
    return await _group_out_with_count(db, group)


@router.get("/{group_id}/members", response_model=list[MemberOut])
async def get_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    members = await group_service.list_members(db, group_id, current_user.id)
    return [MemberOut(**m) for m in members]


@router.post("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await group_service.leave_group(db, group_id, current_user.id)


@router.post("/{group_id}/transfer", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_owner(
    group_id: int,
    body: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await group_service.transfer_owner(db, group_id, current_user.id, body.user_id)
