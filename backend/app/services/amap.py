"""高德地图开放接口客户端（POI 搜索）。"""

import hashlib

import httpx

from app.core.config import get_settings

AMAP_POI_TEXT_URL = "https://restapi.amap.com/v3/place/text"


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
