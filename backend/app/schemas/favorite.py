"""收藏相关请求/响应模型。"""

from pydantic import BaseModel, ConfigDict


class FavoriteStatusOut(BaseModel):
    favorited: bool


class FavoriteItemOut(BaseModel):
    """收藏列表条目：活动摘要 + 收藏时间。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    title: str
    cover_url: str | None = None
    budget: float | None = None
    event_time: object
    status: str
    current_members: int
    max_members: int
    restaurant_name: str | None = None
    favorited_at: object | None = None
