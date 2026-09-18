"""路径规划响应模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class RoutePlanOut(BaseModel):
    mode: Literal["driving", "walking"] = Field(description="出行方式")
    distance_m: float = Field(description="总距离（米）")
    duration_s: int = Field(description="预计耗时（秒）")
    polyline: list[list[float]] = Field(description="路线点串（[经度, 纬度]）")
    mocked: bool = Field(description="是否为无 key 时的 mock 直线降级")
