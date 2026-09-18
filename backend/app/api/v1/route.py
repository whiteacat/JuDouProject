"""路径规划路由（后端代理高德驾车/步行接口）。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.route import RoutePlanOut
from app.services.amap import AmapClient

router = APIRouter(prefix="/route", tags=["route"])


@router.get("/plan", response_model=RoutePlanOut)
async def plan_route(
    origin_lng: float = Query(..., ge=-180, le=180, description="起点经度（GCJ-02）"),
    origin_lat: float = Query(..., ge=-90, le=90, description="起点纬度（GCJ-02）"),
    dest_lng: float = Query(..., ge=-180, le=180, description="终点经度（GCJ-02）"),
    dest_lat: float = Query(..., ge=-90, le=90, description="终点纬度（GCJ-02）"),
    mode: Literal["driving", "walking"] = Query(default="driving", description="出行方式"),
    current_user: User = Depends(get_current_user),
) -> RoutePlanOut:
    try:
        result = await AmapClient().plan_route(
            origin_lng, origin_lat, dest_lng, dest_lat, mode
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"路径规划失败：{exc}",
        ) from exc
    return RoutePlanOut.model_validate(result)
