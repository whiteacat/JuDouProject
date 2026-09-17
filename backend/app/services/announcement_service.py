"""群公告业务逻辑。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.announcement import Announcement
from app.models.group import Group

NOT_OWNER = "仅群主可操作群公告"


async def _get_group(db: AsyncSession, group_id: int) -> Group:
    group = await db.get(Group, group_id)
    if group is None or group.status != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="群组不存在"
        )
    return group


async def _require_owner(db: AsyncSession, group: Group, user_id: int) -> None:
    if group.owner_id != user_id:
        # 成员表兜底校验（转让群主后 groups.owner_id 已同步更新，此处直接比较即可）
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=NOT_OWNER
        )


async def get_announcement(
    db: AsyncSession, group_id: int
) -> Announcement | None:
    """读取群公告（群成员可访问，权限由路由层成员校验保证）。"""
    await _get_group(db, group_id)
    result = await db.execute(
        select(Announcement).where(Announcement.group_id == group_id)
    )
    return result.scalar_one_or_none()


async def upsert_announcement(
    db: AsyncSession, group_id: int, user_id: int, content: str
) -> Announcement:
    """群主发布/更新群公告。"""
    group = await _get_group(db, group_id)
    await _require_owner(db, group, user_id)

    content = content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="公告内容不能为空"
        )

    result = await db.execute(
        select(Announcement).where(Announcement.group_id == group_id)
    )
    announcement = result.scalar_one_or_none()
    if announcement is None:
        announcement = Announcement(
            group_id=group_id, content=content, owner_id=user_id
        )
        db.add(announcement)
    else:
        announcement.content = content
        announcement.owner_id = user_id
    await db.commit()
    await db.refresh(announcement)
    return announcement


async def delete_announcement(
    db: AsyncSession, group_id: int, user_id: int
) -> None:
    """群主删除群公告。"""
    group = await _get_group(db, group_id)
    await _require_owner(db, group, user_id)

    result = await db.execute(
        select(Announcement).where(Announcement.group_id == group_id)
    )
    announcement = result.scalar_one_or_none()
    if announcement is None:
        return
    await db.delete(announcement)
    await db.commit()
