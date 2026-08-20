"""餐厅路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.restaurant import RestaurantOut
from app.services import restaurant_service

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("/search", response_model=list[RestaurantOut])
async def search_restaurants(
    keyword: str = Query(min_length=1, max_length=64, description="搜索关键字"),
    longitude: float = Query(..., ge=-180, le=180, description="中心点经度"),
    latitude: float = Query(..., ge=-90, le=90, description="中心点纬度"),
    radius: int = Query(default=3000, ge=100, le=50000, description="搜索半径（米）"),
    category: str = Query(default="", max_length=64, description="高德 POI 类型"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RestaurantOut]:
    restaurants = await restaurant_service.search_restaurants(
        db, keyword, longitude, latitude, radius, category
    )
    return [RestaurantOut.model_validate(r) for r in restaurants]


@router.get("/{restaurant_id}", response_model=RestaurantOut)
async def get_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RestaurantOut:
    restaurant = await restaurant_service.get_restaurant(db, restaurant_id)
    return RestaurantOut.model_validate(restaurant)
