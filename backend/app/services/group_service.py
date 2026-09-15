"""群组业务逻辑。"""

from __future__ import annotations

import datetime as dt
import secrets

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import GroupEvent
from app.models.event_member import EventMember
from app.models.group import Group
from app.models.member import GroupMember, GroupRole
from app.models.user import User
from app.services import app_setting_service
from app.services import cover as cover_service

GROUP_NOT_FOUND = "群组不存在或无权访问"


def _generate_invite_code() -> str:
    """生成 8 位十六进制邀请码。"""
    return secrets.token_hex(4)


def _require_group(group: Group | None) -> Group:
    if group is None or group.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GROUP_NOT_FOUND)
    return group


async def count_active_members_batch(
    db: AsyncSession, group_ids: list[int]
) -> dict[int, int]:
    """批量统计群组活跃成员数，返回 {group_id: count}。"""
    if not group_ids:
        return {}
    result = await db.execute(
        select(GroupMember.group_id, func.count(GroupMember.id))
        .where(GroupMember.group_id.in_(group_ids), GroupMember.status == 1)
        .group_by(GroupMember.group_id)
    )
    return {group_id: int(count) for group_id, count in result.all()}


async def count_week_active_batch(
    db: AsyncSession, group_ids: list[int]
) -> dict[int, int]:
    """批量统计群组「活跃 N 人」：近 7 天内有活动参与的当前成员数。

    活跃定义（满足其一即算）：
    - 近 7 天内在该群创建过活动（group_events.created_at）
    - 近 7 天内加入过该群任一活动（event_members.joined_at）
    且当前仍为该群有效成员。
    """
    if not group_ids:
        return {}
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    result = await db.execute(
        select(GroupEvent.group_id, GroupEvent.creator_id)
        .where(GroupEvent.group_id.in_(group_ids), GroupEvent.created_at >= since)
    )
    active = {(g, u) for g, u in result.all()}
    result2 = await db.execute(
        select(GroupEvent.group_id, EventMember.user_id)
        .join(EventMember, EventMember.event_id == GroupEvent.id)
        .where(
            GroupEvent.group_id.in_(group_ids),
            EventMember.joined_at >= since,
        )
    )
    active.update({(g, u) for g, u in result2.all()})

    counts: dict[int, int] = {g: 0 for g in group_ids}
    if not active:
        return counts

    member_result = await db.execute(
        select(GroupMember.group_id, GroupMember.user_id).where(
            GroupMember.group_id.in_(group_ids), GroupMember.status == 1
        )
    )
    member_pairs = {(g, u) for g, u in member_result.all()}
    for group_id, user_id in active:
        if (group_id, user_id) in member_pairs:
            counts[group_id] = counts.get(group_id, 0) + 1
    return counts


async def get_membership(
    db: AsyncSession, group_id: int, user_id: int
) -> GroupMember | None:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_group(
    db: AsyncSession,
    user_id: int,
    name: str,
    avatar_url: str = "",
    cover_url: str | None = None,
) -> Group:
    await app_setting_service.ensure_content_edit_enabled(db)
    group = Group(
        name=name,
        avatar_url=avatar_url,
        cover_url=cover_service.validate_group_cover_url(cover_url),
        owner_id=user_id,
        invite_code="",
    )
    # 邀请码唯一性：极低概率冲突时重试
    for _ in range(5):
        code = _generate_invite_code()
        exists = await db.execute(
            select(Group.id).where(Group.invite_code == code)
        )
        if exists.scalar_one_or_none() is None:
            group.invite_code = code
            break
    else:  # pragma: no cover - 5 次冲突概率可忽略
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="邀请码生成失败"
        )

    db.add(group)
    await db.flush()

    db.add(
        GroupMember(group_id=group.id, user_id=user_id, role=GroupRole.OWNER)
    )
    await db.commit()
    await db.refresh(group)
    return group


async def list_my_groups(db: AsyncSession, user_id: int) -> list[Group]:
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.status == 1,
            Group.status == 1,
        )
        .order_by(Group.created_at.desc())
    )
    return list(result.scalars().all())


async def get_group_detail(db: AsyncSession, group_id: int, user_id: int) -> Group:
    group = await db.get(Group, group_id)
    _require_group(group)

    membership = await get_membership(db, group_id, user_id)
    if membership is None or membership.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GROUP_NOT_FOUND)
    return group


async def join_by_code(db: AsyncSession, user_id: int, invite_code: str) -> Group:
    result = await db.execute(
        select(Group).where(Group.invite_code == invite_code)
    )
    group = _require_group(result.scalar_one_or_none())

    membership = await get_membership(db, group.id, user_id)
    if membership is not None:
        if membership.status == 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已在群组中")
        # 之前退出过：恢复成员身份
        membership.status = 1
        await db.commit()
        return group

    db.add(GroupMember(group_id=group.id, user_id=user_id, role=GroupRole.MEMBER))
    await db.commit()
    return group


async def list_members(db: AsyncSession, group_id: int, user_id: int) -> list[dict]:
    await get_group_detail(db, group_id, user_id)
    result = await db.execute(
        select(GroupMember)
        .where(GroupMember.group_id == group_id, GroupMember.status == 1)
        .order_by(GroupMember.joined_at.asc())
    )
    members = result.scalars().all()

    user_ids = [m.user_id for m in members]
    users = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map = {u.id: u for u in users.scalars().all()}

    return [
        {
            "user_id": m.user_id,
            "role": m.role,
            "joined_at": m.joined_at,
            "nickname": user_map[m.user_id].nickname if m.user_id in user_map else "",
            "avatar_url": user_map[m.user_id].avatar_url if m.user_id in user_map else "",
        }
        for m in members
    ]


async def leave_group(db: AsyncSession, group_id: int, user_id: int) -> None:
    group = await db.get(Group, group_id)
    _require_group(group)

    membership = await get_membership(db, group_id, user_id)
    if membership is None or membership.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GROUP_NOT_FOUND)
    if membership.role == GroupRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="群主需先转让群主身份才能退出"
        )

    membership.status = 0
    await db.commit()


async def update_group_cover(
    db: AsyncSession, group_id: int, user_id: int, cover_url: str | None
) -> Group:
    """群主更换群组封面背景（白名单校验；None 清除用默认背景）。"""
    group = await db.get(Group, group_id)
    _require_group(group)

    caller = await get_membership(db, group_id, user_id)
    if caller is None or caller.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GROUP_NOT_FOUND)
    if group.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅群主可修改群组封面")

    group.cover_url = cover_service.validate_group_cover_url(cover_url)
    await db.commit()
    await db.refresh(group)
    return group


async def transfer_owner(
    db: AsyncSession, group_id: int, user_id: int, target_user_id: int
) -> None:
    group = await db.get(Group, group_id)
    _require_group(group)

    caller = await get_membership(db, group_id, user_id)
    if caller is None or caller.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GROUP_NOT_FOUND)
    if caller.role != GroupRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅群主可转让群主身份"
        )
    if target_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能转让给自己"
        )

    target = await get_membership(db, group_id, target_user_id)
    if target is None or target.status != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="接收人必须是群内成员"
        )

    caller.role = GroupRole.ADMIN
    target.role = GroupRole.OWNER
    group.owner_id = target_user_id
    await db.commit()
