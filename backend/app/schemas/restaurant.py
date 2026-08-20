"""餐厅相关响应模型。"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: Optional[str] = None
    category: str
    address: str
    longitude: float
    latitude: float
    phone: Optional[str] = None
    avg_price: Optional[float] = None
    cover_url: Optional[str] = None
    business_hours: Optional[dict] = None
    source: str
    source_id: str
