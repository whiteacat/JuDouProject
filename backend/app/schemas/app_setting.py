"""管理端配置相关模型。"""

from pydantic import BaseModel


class SettingOut(BaseModel):
    key: str
    value: bool
