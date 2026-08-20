"""组队事件相关请求/响应模型。"""

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=64, description="组队标题")
    restaurant_id: Optional[int] = Field(default=None, description="指定餐厅（可空）")
    event_time: dt.datetime = Field(description="聚餐时间")
    min_members: int = Field(default=1, ge=1, le=100)
    max_members: int = Field(ge=1, le=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    remark: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_members(self):
        if self.min_members > self.max_members:
            raise ValueError("min_members 不能大于 max_members")
        return self


class RestaurantBrief(BaseModel):
    id: int
    name: str
    longitude: float
    latitude: float


class EventOut(BaseModel):
    id: int
    group_id: int
    creator_id: int
    title: str
    event_time: dt.datetime
    status: str
    min_members: int
    max_members: int
    current_members: int
    remark: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    restaurant: Optional[RestaurantBrief] = None


class EventMemberOut(BaseModel):
    user_id: int
    joined_at: dt.datetime
    nickname: str
    avatar_url: str
