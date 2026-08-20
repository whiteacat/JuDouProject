"""JWT 签发与解析。"""

import datetime as dt
from uuid import uuid4

import jwt

from app.core.config import get_settings


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),  # 保证同秒内多次签发的 token 各不相同，后续可用于吊销
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """解析 token 并返回 user_id；无效或过期抛出 jwt.InvalidTokenError。"""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
