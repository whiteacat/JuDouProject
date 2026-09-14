"""群公告相关请求/响应模型。"""

from pydantic import BaseModel, ConfigDict, Field


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    content: str
    owner_id: int
    created_at: object
    updated_at: object


class AnnouncementCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500, description="公告内容")
