"""组队事件相关请求/响应模型。"""

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field, model_validator

VALID_EXPIRY_MODES = ("none", "at_complete", "at_time", "after_hours")

# 成员时间窗口限制：日期跨度上限（天）、每人总段数上限
MAX_WINDOW_SEGMENTS = 30


class TimeWindow(BaseModel):
    """成员可参加的一个时段：某一天内的 [start, end)（HH:mm，同日不跨午夜）。"""

    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="日期 YYYY-MM-DD")
    start: str = Field(pattern=r"^\d{2}:\d{2}$", description="开始 HH:mm")
    end: str = Field(pattern=r"^\d{2}:\d{2}$", description="结束 HH:mm")

    @model_validator(mode="after")
    def check_segment(self):
        try:
            dt.datetime.strptime(self.date, "%Y-%m-%d")
            start_t = dt.datetime.strptime(self.start, "%H:%M")
            end_t = dt.datetime.strptime(self.end, "%H:%M")
        except ValueError:
            raise ValueError("日期或时间格式不合法（应为 YYYY-MM-DD / HH:mm）")
        if end_t <= start_t:
            raise ValueError("时段结束必须晚于开始")
        return self


def _validate_window_list(windows: list[TimeWindow]):
    """多段窗口整体校验：数量上限、同日期不重叠。"""
    if len(windows) > MAX_WINDOW_SEGMENTS:
        raise ValueError(f"时间窗口段数不能超过 {MAX_WINDOW_SEGMENTS} 段")
    by_date: dict[str, list[tuple[int, int, int]]] = {}
    seen = set()
    for w in windows:
        key = (w.date, w.start, w.end)
        if key in seen:
            raise ValueError("存在重复的时间段")
        seen.add(key)
        s = int(w.start[:2]) * 60 + int(w.start[3:])
        e = int(w.end[:2]) * 60 + int(w.end[3:])
        by_date.setdefault(w.date, []).append((s, e, len(by_date.get(w.date, []))))
    for date, segs in by_date.items():
        segs.sort()
        for (s1, e1, _), (s2, _e2, _) in zip(segs, segs[1:]):
            if s2 < e1:
                raise ValueError(f"{date} 存在重叠的时间段")


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=64, description="组队标题")
    restaurant_id: Optional[int] = Field(default=None, description="指定餐厅（可空）")
    event_time: dt.datetime = Field(description="聚餐时间")
    min_members: int = Field(default=1, ge=1, le=100)
    max_members: int = Field(ge=1, le=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    remark: Optional[str] = Field(default=None, max_length=500)
    # 失效策略：none 长期有效 / at_complete 完成才失效 / at_time 指定时间 / after_hours 创建后 N 小时
    expiry_mode: str = Field(default="none", max_length=16)
    expires_at: Optional[dt.datetime] = Field(
        default=None, description="失效时间（expiry_mode=at_time 时必填）"
    )
    expires_after_hours: Optional[int] = Field(
        default=None, ge=1, le=24 * 365, description="创建后 N 小时失效（expiry_mode=after_hours 时必填）"
    )
    # 创建者本人可参加时段（可跨多天、每天多段；后续可单独调整）
    time_windows: list[TimeWindow] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_members(self):
        if self.min_members > self.max_members:
            raise ValueError("min_members 不能大于 max_members")
        return self

    @model_validator(mode="after")
    def check_expiry(self):
        if self.expiry_mode not in VALID_EXPIRY_MODES:
            raise ValueError(f"expiry_mode 必须是 {VALID_EXPIRY_MODES} 之一")
        if self.expiry_mode == "at_time" and self.expires_at is None:
            raise ValueError("expiry_mode=at_time 时必须提供 expires_at")
        if self.expiry_mode == "after_hours" and self.expires_after_hours is None:
            raise ValueError("expiry_mode=after_hours 时必须提供 expires_after_hours")
        if self.expiry_mode in ("none", "at_complete"):
            self.expires_at = None
            self.expires_after_hours = None
        return self

    @model_validator(mode="after")
    def check_windows(self):
        _validate_window_list(self.time_windows)
        return self


class EventJoin(BaseModel):
    """加入组队（可选携带本人可参加时段）。"""

    time_windows: list[TimeWindow] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_windows(self):
        _validate_window_list(self.time_windows)
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
    expiry_mode: str = "none"
    expires_at: Optional[dt.datetime] = None


class EventMemberOut(BaseModel):
    user_id: int
    joined_at: dt.datetime
    nickname: str
    avatar_url: str
    time_windows: list[TimeWindow] = Field(default_factory=list)
