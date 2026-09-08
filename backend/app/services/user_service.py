"""用户业务逻辑。"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.sensitive import check_nickname


async def get_or_create_user(
    db: AsyncSession,
    openid: str,
    unionid: Optional[str] = None,
    nickname: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> User:
    """按 openid 查找用户；不存在则创建，已存在则回填缺失字段。"""
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            openid=openid,
            unionid=unionid,
            nickname=nickname or "微信用户",
            avatar_url=avatar_url or "",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        changed = False
        if unionid and not user.unionid:
            user.unionid = unionid
            changed = True
        if nickname and nickname != user.nickname:
            user.nickname = nickname
            changed = True
        if avatar_url and avatar_url != user.avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
    return user


class ProfileUpdateError(Exception):
    """资料修改校验失败。"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def update_user_profile(
    db: AsyncSession,
    user: User,
    nickname: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> User:
    """修改用户昵称/头像，含敏感词校验。

    Raises:
        ProfileUpdateError: 校验不通过时抛出。
    """
    changed = False

    if nickname is not None:
        reason = check_nickname(nickname)
        if reason:
            raise ProfileUpdateError(reason)
        if nickname != user.nickname:
            user.nickname = nickname
            changed = True

    if avatar_url is not None:
        if len(avatar_url) > 512:
            raise ProfileUpdateError("头像 URL 过长")
        if avatar_url != user.avatar_url:
            user.avatar_url = avatar_url
            changed = True

    if changed:
        await db.commit()
        await db.refresh(user)

    return user
