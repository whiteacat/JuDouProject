"""登录相关请求/响应模型。"""

from pydantic import BaseModel, Field

from app.schemas.user import UserOut


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128, description="wx.login 返回的临时登录凭证")
    nickname: str | None = Field(default=None, max_length=64, description="用户昵称（小程序选填）")
    avatar_url: str | None = Field(default=None, max_length=512, description="用户头像 URL（小程序选填）")


class LoginResponse(BaseModel):
    access_token: str
    user: UserOut
