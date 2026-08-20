"""餐厅接口测试（mock 高德模式 + 真实数据库）。

覆盖：搜索鉴权、参数校验、mock 搜索、upsert 幂等、详情、404。
"""

SEARCH_URL = "/api/v1/restaurants/search"
LOGIN_URL = "/api/v1/auth/wechat/login"

LNG, LAT = 116.4, 39.9  # 北京中心附近


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client) -> str:
    resp = await client.post(LOGIN_URL, json={"code": "rest_user"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _search(client, token: str, keyword: str = "火锅", **extra):
    params = {"keyword": keyword, "longitude": LNG, "latitude": LAT, **extra}
    return await client.get(SEARCH_URL, params=params, headers=_auth(token))


async def test_search_requires_auth(client):
    resp = await client.get(
        SEARCH_URL, params={"keyword": "火锅", "longitude": LNG, "latitude": LAT}
    )
    assert resp.status_code == 401


async def test_search_missing_coords_422(require_db, client):
    token = await _login(client)
    resp = await client.get(SEARCH_URL, params={"keyword": "火锅"}, headers=_auth(token))
    assert resp.status_code == 422


async def test_search_mock_mode(require_db, client):
    token = await _login(client)
    resp = await _search(client, token)
    assert resp.status_code == 200, resp.text
    restaurants = resp.json()
    assert len(restaurants) == 5  # mock 生成 5 家
    for r in restaurants:
        assert r["name"].startswith("火锅")
        assert r["source"] == "amap"
        assert r["source_id"]
        assert -180 <= r["longitude"] <= 180
        assert -90 <= r["latitude"] <= 90


async def test_search_upsert_idempotent(require_db, client):
    token = await _login(client)
    first = (await _search(client, token)).json()
    second = (await _search(client, token)).json()
    first_ids = [r["id"] for r in first]
    second_ids = [r["id"] for r in second]
    assert first_ids == second_ids  # 同关键字多次搜索复用同一批记录
    assert len(set(first_ids)) == len(first_ids)


async def test_search_different_keywords(require_db, client):
    token = await _login(client)
    hotpot = (await _search(client, token, keyword="火锅")).json()
    bbq = (await _search(client, token, keyword="烧烤")).json()
    hotpot_ids = {r["source_id"] for r in hotpot}
    bbq_ids = {r["source_id"] for r in bbq}
    assert hotpot_ids.isdisjoint(bbq_ids)


async def test_get_restaurant_detail(require_db, client):
    token = await _login(client)
    search_resp = await _search(client, token)
    target = search_resp.json()[0]

    resp = await client.get(
        f"/api/v1/restaurants/{target['id']}", headers=_auth(token)
    )
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == target["id"]
    assert detail["name"] == target["name"]
    assert detail["longitude"] == target["longitude"]
    assert detail["latitude"] == target["latitude"]


async def test_get_restaurant_not_found(require_db, client):
    token = await _login(client)
    resp = await client.get("/api/v1/restaurants/999999", headers=_auth(token))
    assert resp.status_code == 404
