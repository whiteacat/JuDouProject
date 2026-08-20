"""MVP 全链路闭环集成测试（§39 验收）。

登录 → 建群 → 邀请加入 → 地图查组队 → 找餐厅 → 组队 → 加入(满员确认)
→ 完成(餐厅入库) → 评价(聚合) → 群组餐厅库 → 再组队(visit_count=2)，
以及取消 / 满员 / 过期等异常路径。
"""

import datetime as dt
import uuid

BASE = "/api/v1"
LOGIN_URL = f"{BASE}/auth/wechat/login"

LNG, LAT = 116.4, 39.9


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _future(hours: int = 3) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)).isoformat()


async def _login(client, code: str) -> tuple[str, int]:
    resp = await client.post(LOGIN_URL, json={"code": code})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["access_token"], body["user"]["id"]


async def test_full_mvp_loop(require_db, client):
    tag = uuid.uuid4().hex[:8]

    # 1. 三个用户登录
    token_a, _ = await _login(client, f"fl_{tag}_a")
    token_b, _ = await _login(client, f"fl_{tag}_b")
    token_c, _ = await _login(client, f"fl_{tag}_c")

    # 2. A 建群，B/C 用邀请码加入
    group = (
        await client.post(
            f"{BASE}/groups", json={"name": f"闭环群{tag}"}, headers=_auth(token_a)
        )
    ).json()
    gid, invite = group["id"], group["invite_code"]
    for t in (token_b, token_c):
        resp = await client.post(
            f"{BASE}/groups/join-by-code",
            json={"invite_code": invite},
            headers=_auth(t),
        )
        assert resp.status_code == 200, resp.text

    # 3. A 搜索餐厅（mock 高德）
    search = await client.get(
        f"{BASE}/restaurants/search",
        params={"keyword": "火锅", "longitude": LNG, "latitude": LAT},
        headers=_auth(token_a),
    )
    assert search.status_code == 200
    rid = search.json()[0]["id"]

    # 4. A 创建组队（指定餐厅，上限 3 人）
    event1 = (
        await client.post(
            f"{BASE}/groups/{gid}/events",
            json={
                "title": "首次聚餐",
                "event_time": _future(),
                "min_members": 1,
                "max_members": 3,
                "restaurant_id": rid,
            },
            headers=_auth(token_a),
        )
    ).json()
    assert event1["current_members"] == 1

    # 5. B 地图查询能看到该组队（§35：B 地图看到）
    m = await client.get(
        f"{BASE}/groups/{gid}/events/map",
        params={"longitude": LNG, "latitude": LAT, "radius": 5000},
        headers=_auth(token_b),
    )
    assert m.status_code == 200
    assert any(e["id"] == event1["id"] for e in m.json())

    # 6. B/C 加入 → 满员自动 CONFIRMED
    for t in (token_b, token_c):
        resp = await client.post(
            f"{BASE}/events/{event1['id']}/join", headers=_auth(t)
        )
        assert resp.status_code == 200, resp.text
    detail = (
        await client.get(f"{BASE}/events/{event1['id']}", headers=_auth(token_a))
    ).json()
    assert detail["status"] == "CONFIRMED"
    assert detail["current_members"] == 3

    # 7. A 完成聚餐 → 餐厅自动入群餐厅库（visit=1）
    resp = await client.post(
        f"{BASE}/events/{event1['id']}/complete", headers=_auth(token_a)
    )
    assert resp.status_code == 204
    lib = (
        await client.get(
            f"{BASE}/groups/{gid}/restaurants/{rid}", headers=_auth(token_a)
        )
    ).json()
    assert lib["group_stats"]["visit_count"] == 1

    # 8. 三人各评价一次 → 聚合评分 = AVG(5,4,3) = 4.0
    for i, t in enumerate((token_a, token_b, token_c)):
        resp = await client.post(
            f"{BASE}/events/{event1['id']}/reviews",
            json={
                "overall_score": 5 - i,
                "taste_score": 5,
                "value_score": 4,
                "environment_score": 4,
                "service_score": 4,
                "traffic_score": 4,
                "content": f"评价{i}",
            },
            headers=_auth(t),
        )
        assert resp.status_code == 201, resp.text
    stats = (
        await client.get(
            f"{BASE}/groups/{gid}/restaurants/{rid}", headers=_auth(token_a)
        )
    ).json()["group_stats"]
    assert stats["score"] == 4.0
    assert stats["visit_count"] == 1

    # 9. 再组队：同一餐厅第二次 → 完成 → visit_count=2
    event2 = (
        await client.post(
            f"{BASE}/groups/{gid}/events",
            json={
                "title": "二刷",
                "event_time": _future(),
                "min_members": 1,
                "max_members": 3,
                "restaurant_id": rid,
            },
            headers=_auth(token_a),
        )
    ).json()
    resp = await client.post(
        f"{BASE}/events/{event2['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 200
    resp = await client.post(
        f"{BASE}/events/{event2['id']}/complete", headers=_auth(token_a)
    )
    assert resp.status_code == 204
    stats2 = (
        await client.get(
            f"{BASE}/groups/{gid}/restaurants/{rid}", headers=_auth(token_a)
        )
    ).json()["group_stats"]
    assert stats2["visit_count"] == 2

    # 10. 异常路径：满员（max=2：创建者占 1 席，B 加入满员后再加入 → 409）
    event3 = (
        await client.post(
            f"{BASE}/groups/{gid}/events",
            json={
                "title": "满员测试",
                "event_time": _future(),
                "min_members": 1,
                "max_members": 2,
                "latitude": LAT,
                "longitude": LNG,
            },
            headers=_auth(token_a),
        )
    ).json()
    resp = await client.post(
        f"{BASE}/events/{event3['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 200  # B 加入后 2/2 满员
    resp = await client.post(
        f"{BASE}/events/{event3['id']}/join", headers=_auth(token_c)
    )
    assert resp.status_code == 409

    # 11. 异常路径：取消后不可加入
    event4 = (
        await client.post(
            f"{BASE}/groups/{gid}/events",
            json={
                "title": "取消测试",
                "event_time": _future(),
                "min_members": 1,
                "max_members": 2,
                "latitude": LAT,
                "longitude": LNG,
            },
            headers=_auth(token_a),
        )
    ).json()
    resp = await client.post(
        f"{BASE}/events/{event4['id']}/cancel", headers=_auth(token_a)
    )
    assert resp.status_code == 204
    resp = await client.post(
        f"{BASE}/events/{event4['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 400

    # 12. 异常路径：过期（创建时用过去时间 → 400；已过期组队不可加入 → 400）
    past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
    resp = await client.post(
        f"{BASE}/groups/{gid}/events",
        json={
            "title": "过期测试",
            "event_time": past,
            "min_members": 1,
            "max_members": 2,
            "latitude": LAT,
            "longitude": LNG,
        },
        headers=_auth(token_a),
    )
    assert resp.status_code == 400

    event5 = (
        await client.post(
            f"{BASE}/groups/{gid}/events",
            json={
                "title": "过期加入测试",
                "event_time": _future(),
                "min_members": 1,
                "max_members": 2,
                "latitude": LAT,
                "longitude": LNG,
            },
            headers=_auth(token_a),
        )
    ).json()
    from sqlalchemy import update

    from app.db.session import async_session_factory
    from app.models.event import GroupEvent

    async with async_session_factory() as db:
        await db.execute(
            update(GroupEvent)
            .where(GroupEvent.id == event5["id"])
            .values(
                event_time=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
            )
        )
        await db.commit()
    resp = await client.post(
        f"{BASE}/events/{event5['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 400

    # 13. 我的组队列表能查到两次组队
    mine = (await client.get(f"{BASE}/events/mine", headers=_auth(token_a))).json()
    ids = {e["id"] for e in mine}
    assert event1["id"] in ids and event2["id"] in ids
