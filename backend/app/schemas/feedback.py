"""反馈相关请求模型。"""

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500, description="反馈内容")
    contact: str | None = Field(default=None, max_length=64, description="联系方式（选填）")
    kind: str = Field(default="other", description="bug / suggestion / other")

    @property
    def kind_ok(self) -> bool:
        return self.kind in ("bug", "suggestion", "other")
