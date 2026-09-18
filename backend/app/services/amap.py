"""高德地图开放接口客户端（POI 搜索 + 路径规划）。"""

import hashlib
import math

import httpx

from app.core.config import get_settings

AMAP_POI_TEXT_URL = "https://restapi.amap.com/v3/place/text"
AMAP_DRIVING_URL = "https://restapi.amap.com/v3/direction/driving"
AMAP_WALKING_URL = "https://restapi.amap.com/v3/direction/walking"

ROUTE_MODES = ("driving", "walking")

# mock 降级时的估算速度（米/秒）：驾车 40km/h，步行 4km/h
_MOCK_SPEED = {"driving": 40 / 3.6, "walking": 4 / 3.6}


class AmapClient:
    """封装高德 POI 搜索。

    未配置 AMAP_KEY 时进入 mock 模式：围绕中心点生成若干假餐厅，
    source_id 由关键字哈希派生，保证多次搜索 upsert 幂等。
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def search_poi(
        self,
        keyword: str,
        longitude: float,
        latitude: float,
        radius: int = 3000,
        category: str = "",
    ) -> list[dict]:
        if not self.settings.amap_key:
            return self._mock_pois(keyword, longitude, latitude, category)

        params = {
            "key": self.settings.amap_key,
            "keywords": keyword,
            "location": f"{longitude},{latitude}",
            "radius": str(radius or 3000),
            "offset": "20",
            "page": "1",
            "extensions": "base",
        }
        if category:
            params["types"] = category

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(AMAP_POI_TEXT_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "1":
            raise ValueError(f"amap poi search failed: {data}")

        pois = []
        for poi in data.get("pois", []) or []:
            lng, lat = ("", "")
            if poi.get("location"):
                lng, lat = poi["location"].split(",", 1)
            pois.append(
                {
                    "source_id": poi.get("id") or "",
                    "name": poi.get("name") or "",
                    "category": (poi.get("type") or "").split(";")[0],
                    "address": poi.get("address") or "",
                    "longitude": float(lng) if lng else 0.0,
                    "latitude": float(lat) if lat else 0.0,
                    "phone": poi.get("tel") or None,
                    "brand": None,
                    "avg_price": None,
                    "cover_url": None,
                    "business_hours": None,
                }
            )
        return pois

    def _mock_pois(
        self, keyword: str, longitude: float, latitude: float, category: str
    ) -> list[dict]:
        base = hashlib.md5(f"{keyword}:{category}".encode()).hexdigest()[:8]
        names = ["老店", "旗舰店", "二店", "分店", "总店"]
        pois = []
        for i, suffix in enumerate(names):
            dlng = (i % 3 - 1) * 0.004
            dlat = (i // 3) * 0.003 + 0.002
            pois.append(
                {
                    "source_id": f"mock_{base}_{i}",
                    "name": f"{keyword}{suffix}",
                    "category": category or "美食",
                    "address": f"mock 地址 {i + 1} 号",
                    "longitude": round(float(longitude) + dlng, 7),
                    "latitude": round(float(latitude) + dlat, 7),
                    "phone": None,
                    "brand": None,
                    "avg_price": None,
                    "cover_url": None,
                    "business_hours": None,
                }
            )
        return pois

    async def plan_route(
        self,
        origin_lng: float,
        origin_lat: float,
        dest_lng: float,
        dest_lat: float,
        mode: str = "driving",
    ) -> dict:
        if mode not in ROUTE_MODES:
            raise ValueError(f"mode 必须是 {ROUTE_MODES} 之一")
        if not self.settings.amap_key:
            return _mock_route(origin_lng, origin_lat, dest_lng, dest_lat, mode)

        url = AMAP_DRIVING_URL if mode == "driving" else AMAP_WALKING_URL
        params = {
            "key": self.settings.amap_key,
            "origin": f"{origin_lng},{origin_lat}",
            "destination": f"{dest_lng},{dest_lat}",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "1":
            raise ValueError(f"amap route plan failed: {data}")

        paths = (data.get("route") or {}).get("paths") or []
        if not paths:
            raise ValueError(f"amap route plan empty: {data}")
        best = paths[0]
        points: list[list[float]] = []
        for step in best.get("steps") or []:
            for pair in (step.get("polyline") or "").split(";"):
                if "," not in pair:
                    continue
                lng, lat = pair.split(",", 1)
                points.append([float(lng), float(lat)])
        return {
            "mode": mode,
            "distance_m": float(best.get("distance") or 0),
            "duration_s": int(float(best.get("duration") or 0)),
            "polyline": points,
            "mocked": False,
        }


def _haversine_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    radius = 6371000.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _mock_route(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
    mode: str,
) -> dict:
    distance = _haversine_m(origin_lng, origin_lat, dest_lng, dest_lat)
    steps = 24
    points = [
        [
            origin_lng + (dest_lng - origin_lng) * i / steps,
            origin_lat + (dest_lat - origin_lat) * i / steps,
        ]
        for i in range(steps + 1)
    ]
    return {
        "mode": mode,
        "distance_m": round(distance, 1),
        "duration_s": int(distance / _MOCK_SPEED[mode]) if distance else 0,
        "polyline": points,
        "mocked": True,
    }
