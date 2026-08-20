"""登录相关请求/响应模型。"""

from pydantic import BaseModel, Field

from app.schemas.user import UserOut


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128, description="wx.login 返回的临时登录凭证")


class LoginResponse(BaseModel):
    access_token: str
    user: UserOut
