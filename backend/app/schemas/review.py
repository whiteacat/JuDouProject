"""评价与群组餐厅库相关请求/响应模型。"""

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.restaurant import RestaurantOut


class ReviewCreate(BaseModel):
    """提交评价：五维评分（总分由服务端加权计算，不单独提交）。"""

    taste_score: float = Field(ge=1, le=5, description="口味")
    value_score: float = Field(ge=1, le=5, description="性价比")
    environment_score: float = Field(ge=1, le=5, description="环境")
    service_score: float = Field(ge=1, le=5, description="服务")
    traffic_score: float = Field(ge=1, le=5, description="交通便利")
    content: str = Field(default="", max_length=500, description="文字评价")


class ReviewOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    avatar_url: str
    overall_score: float
    taste_score: float
    value_score: float
    environment_score: float
    service_score: float
    traffic_score: float
    content: str
    created_at: dt.datetime


class MyReviewOut(BaseModel):
    """我的评价：附餐厅/群/组队信息。"""

    id: int
    restaurant_id: int
    restaurant_name: str
    group_id: int
    group_name: Optional[str] = None
    event_id: int
    event_title: Optional[str] = None
    overall_score: float
    content: str
    created_at: dt.datetime


class GroupStats(BaseModel):
    visit_count: int
    score: Optional[float] = None
    taste: Optional[float] = None
    value: Optional[float] = None
    environment: Optional[float] = None
    service: Optional[float] = None
    traffic: Optional[float] = None


class GroupRestaurantOut(BaseModel):
    """群组餐厅库条目：餐厅信息 + 群聚合评分（§20 响应结构）。"""

    restaurant: RestaurantOut
    group_stats: GroupStats
