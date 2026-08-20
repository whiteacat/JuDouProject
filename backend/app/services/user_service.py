"""用户业务逻辑。"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_or_create_user(
    db: AsyncSession, openid: str, unionid: Optional[str] = None
) -> User:
    """按 openid 查找用户；不存在则创建。已存在且补传了 unionid 时回填。"""
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(openid=openid, unionid=unionid)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif unionid and not user.unionid:
        user.unionid = unionid
        await db.commit()
        await db.refresh(user)
    return user
