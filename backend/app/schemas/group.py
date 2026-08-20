"""群组相关请求/响应模型。"""

import datetime as dt

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, description="群组名称")
    avatar_url: str = Field(default="", max_length=512)


class GroupOut(BaseModel):
    id: int
    name: str
    avatar_url: str
    owner_id: int
    invite_code: str
    member_count: int = 0
    created_at: dt.datetime


class JoinByCodeRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=16)


class MemberOut(BaseModel):
    user_id: int
    role: str
    joined_at: dt.datetime
    nickname: str
    avatar_url: str


class TransferRequest(BaseModel):
    user_id: int
