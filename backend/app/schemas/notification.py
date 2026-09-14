"""站内通知相关响应模型。"""

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    content: str
    target_type: str | None
    target_id: int | None
    actor_name: str | None
    is_read: bool
    created_at: object


class UnreadCountOut(BaseModel):
    count: int
