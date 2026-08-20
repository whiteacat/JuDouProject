"""用户相关响应模型。"""

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    avatar_url: str


class UserStatsOut(BaseModel):
    group_count: int
    event_count: int
    review_count: int
