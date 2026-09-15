"""FastAPI 依赖：当前登录用户。"""

from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    try:
        user_id = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证"
        ) from None

    user = await db.get(User, user_id)
    if user is None or user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


async def get_current_user_or_anonymous(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    token: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选登录：优先 Authorization 头，其次 ?token= query（canvas 的
    createImage 无法携带请求头，海报二维码等端点靠 query 兜底）。

    凭证缺失或无效时返回 None（端点自行决定匿名行为），不抛 401。
    """
    raw: str | None = credentials.credentials if credentials else token
    if not raw:
        return None
    try:
        user_id = decode_access_token(raw)
    except Exception:
        return None
    user = await db.get(User, user_id)
    if user is None or user.status != 1:
        return None
    return user
