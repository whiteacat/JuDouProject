"""用户相关请求/响应模型。"""

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    avatar_url: str
    signature: str | None = None


class UserUpdateRequest(BaseModel):
    """用户资料修改请求。字段均为可选，只传需要修改的。"""

    nickname: str | None = Field(default=None, min_length=1, max_length=20, description="新昵称")
    avatar_url: str | None = Field(default=None, max_length=512, description="新头像 URL")
    signature: str | None = Field(default=None, max_length=100, description="个性签名")


# 预设头像列表（小程序端同步维护，后端用于白名单校验）
PRESET_AVATARS: list[str] = [
    "preset://avatar/1",
    "preset://avatar/2",
    "preset://avatar/3",
    "preset://avatar/4",
    "preset://avatar/5",
    "preset://avatar/6",
    "preset://avatar/7",
    "preset://avatar/8",
]


class UserStatsOut(BaseModel):
    group_count: int
    event_count: int
    review_count: int
