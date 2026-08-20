"""认证路由：微信登录。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import LoginResponse, WechatLoginRequest
from app.schemas.user import UserOut
from app.services.user_service import get_or_create_user
from app.services.wechat import WechatClient

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/wechat/login", response_model=LoginResponse)
async def wechat_login(
    body: WechatLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    session = await WechatClient().code2session(body.code)
    user = await get_or_create_user(db, session["openid"], session.get("unionid"))
    token = create_access_token(user.id)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))
