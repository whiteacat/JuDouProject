"""群组路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreateRequest,
    AnnouncementOut,
)
from app.schemas.group import (
    GroupCoverUpdate,
    GroupCreate,
    GroupOut,
    JoinByCodeRequest,
    MemberOut,
    TransferRequest,
)
from app.services import announcement_service, group_service

router = APIRouter(prefix="/groups", tags=["groups"])


def _group_to_out(group, member_count: int, active_count: int = 0) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        avatar_url=group.avatar_url,
        cover_url=group.cover_url,
        owner_id=group.owner_id,
        invite_code=group.invite_code,
        member_count=member_count,
        active_count=active_count,
        created_at=group.created_at,
    )


async def _group_out_with_count(db: AsyncSession, group) -> GroupOut:
    counts = await group_service.count_active_members_batch(db, [group.id])
    active = await group_service.count_week_active_batch(db, [group.id])
    return _group_to_out(group, counts.get(group.id, 1), active.get(group.id, 0))


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupOut:
    group = await group_service.create_group(
        db, current_user.id, body.name, body.avatar_url, body.cover_url
    )
    return await _group_out_with_count(db, group)


@router.patch("/{group_id}/cover", response_model=GroupOut)
async def update_group_cover(
    group_id: int,
    body: GroupCoverUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupOut:
    """群主更换群组封面背景（预设白名单；cover_url=null 清除用默认背景）。"""
    group = await group_service.update_group_cover(
        db, group_id, current_user.id, body.cover_url
    )
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
    active = await group_service.count_week_active_batch(db, [g.id for g in groups])
    return [
        _group_to_out(g, counts.get(g.id, 1), active.get(g.id, 0)) for g in groups
    ]


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


@router.get("/{group_id}/announcement", response_model=AnnouncementOut)
async def get_group_announcement(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnouncementOut:
    """读取群公告（群成员可见；无公告返回 404）。"""
    await group_service.get_group_detail(db, group_id, current_user.id)
    announcement = await announcement_service.get_announcement(db, group_id)
    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="暂无群公告"
        )
    return announcement


@router.put("/{group_id}/announcement", response_model=AnnouncementOut)
async def upsert_group_announcement(
    group_id: int,
    body: AnnouncementCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnouncementOut:
    """群主发布/更新群公告。"""
    return await announcement_service.upsert_announcement(
        db, group_id, current_user.id, body.content
    )


@router.delete("/{group_id}/announcement", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_announcement(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """群主删除群公告。"""
    await announcement_service.delete_announcement(db, group_id, current_user.id)
