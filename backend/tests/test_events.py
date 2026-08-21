"""组队事件接口测试（mock 高德 + 真实数据库）。

覆盖：创建、地图查询、加入、并发满员、重复加入、退出、状态流转、权限。
"""

import asyncio
import datetime as dt

EVENTS_URL = "/api/v1"
LOGIN_URL = "/api/v1/auth/wechat/login"

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


async def _group_with_second(client, code_a: str, code_b: str) -> tuple[int, str, str]:
    token_a, _ = await _login(client, code_a)
    group = (
        await client.post(
            "/api/v1/groups", json={"name": "组队测试群"}, headers=_auth(token_a)
        )
    ).json()
    token_b, _ = await _login(client, code_b)
    await client.post(
        "/api/v1/groups/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    return group["id"], token_a, group["invite_code"]


async def _add_member(client, invite_code: str, code: str) -> str:
    """将用户加入群组（组队的前提是群成员），返回其 token。"""
    token, _ = await _login(client, code)
    resp = await client.post(
        "/api/v1/groups/join-by-code",
        json={"invite_code": invite_code},
        headers=_auth(token),
    )
    assert resp.status_code in (200, 409), resp.text  # 已在群中视为成功
    return token


async def _create_event(
    client, token: str, group_id: int, max_members: int = 6, **extra
) -> dict:
    payload = {
        "title": "周五聚餐",
        "event_time": _future(),
        "min_members": 1,
        "max_members": max_members,
        **extra,
    }
    resp = await client.post(
        f"{EVENTS_URL}/groups/{group_id}/events",
        json=payload,
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- 创建 ----------


async def test_create_event_requires_auth(client):
    resp = await client.post(
        f"{EVENTS_URL}/groups/1/events",
        json={"title": "x", "event_time": _future(), "max_members": 2},
    )
    assert resp.status_code == 401


async def test_create_event_non_member_forbidden(require_db, client):
    token, _ = await _login(client, "ev_nm_a")
    group_id, _ , _ic = await _group_with_second(client, "ev_nm_b", "ev_nm_b2")
    outsider, _ = await _login(client, "ev_nm_x")
    resp = await client.post(
        f"{EVENTS_URL}/groups/{group_id}/events",
        json={"title": "x", "event_time": _future(), "max_members": 2},
        headers=_auth(outsider),
    )
    assert resp.status_code == 403


async def test_create_event_auto_join_creator(require_db, client):
    group_id, token , _ic = await _group_with_second(client, "ev_c_a", "ev_c_b")
    event = await _create_event(client, token, group_id)
    assert event["current_members"] == 1
    assert event["status"] == "RECRUITING"
    assert event["creator_id"] == (await _login(client, "ev_c_a"))[1]


async def test_create_event_invalid_members_422(require_db, client):
    group_id, token , _ic = await _group_with_second(client, "ev_422_a", "ev_422_b")
    resp = await client.post(
        f"{EVENTS_URL}/groups/{group_id}/events",
        json={"title": "x", "event_time": _future(), "min_members": 5, "max_members": 2},
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_create_event_past_time_400(require_db, client):
    group_id, token , _ic = await _group_with_second(client, "ev_t_a", "ev_t_b")
    past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
    resp = await client.post(
        f"{EVENTS_URL}/groups/{group_id}/events",
        json={"title": "x", "event_time": past, "max_members": 2},
        headers=_auth(token),
    )
    assert resp.status_code == 400


async def test_create_event_with_restaurant_uses_coords(require_db, client):
    group_id, token , _ic = await _group_with_second(client, "ev_r_a", "ev_r_b")
    search = await client.get(
        "/api/v1/restaurants/search",
        params={"keyword": "火锅", "longitude": LNG, "latitude": LAT},
        headers=_auth(token),
    )
    restaurant = search.json()[0]
    event = await _create_event(client, token, group_id, restaurant_id=restaurant["id"])
    assert event["restaurant"]["id"] == restaurant["id"]
    assert event["latitude"] == restaurant["latitude"]
    assert event["longitude"] == restaurant["longitude"]


# ---------- 地图查询 ----------


async def test_map_events_requires_group_member(require_db, client):
    group_id, _ , _ic = await _group_with_second(client, "ev_m_a", "ev_m_b")
    outsider, _ = await _login(client, "ev_m_x")
    resp = await client.get(
        f"{EVENTS_URL}/groups/{group_id}/events/map", headers=_auth(outsider)
    )
    assert resp.status_code == 403


async def test_map_events_radius_filter(require_db, client):
    group_id, token , _ic = await _group_with_second(client, "ev_rad_a", "ev_rad_b")
    await _create_event(
        client, token, group_id, latitude=LAT + 0.01, longitude=LNG
    )  # 约 1.1km，范围内
    far = await _create_event(
        client, token, group_id, latitude=LAT, longitude=LNG + 1.0
    )  # 约 78km，范围外

    resp = await client.get(
        f"{EVENTS_URL}/groups/{group_id}/events/map",
        params={"longitude": LNG, "latitude": LAT, "radius": 3000},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    ids = [e["id"] for e in resp.json()]
    assert far["id"] not in ids
    assert len(ids) >= 1


async def test_map_events_group_isolation(require_db, client):
    """群组切换视角（§40）：A 群的组队不出现在 B 群的地图查询中。"""
    token, _ = await _login(client, "ev_iso_a")
    g1 = (
        await client.post(
            f"{EVENTS_URL}/groups", json={"name": "群A"}, headers=_auth(token)
        )
    ).json()
    g2 = (
        await client.post(
            f"{EVENTS_URL}/groups", json={"name": "群B"}, headers=_auth(token)
        )
    ).json()
    event = await _create_event(client, token, g1["id"], latitude=LAT, longitude=LNG)

    m1 = await client.get(
        f"{EVENTS_URL}/groups/{g1['id']}/events/map",
        params={"longitude": LNG, "latitude": LAT, "radius": 5000},
        headers=_auth(token),
    )
    m2 = await client.get(
        f"{EVENTS_URL}/groups/{g2['id']}/events/map",
        params={"longitude": LNG, "latitude": LAT, "radius": 5000},
        headers=_auth(token),
    )
    ids1 = {e["id"] for e in m1.json()}
    ids2 = {e["id"] for e in m2.json()}
    assert event["id"] in ids1  # 群 A 可见
    assert event["id"] not in ids2  # 群 B 不可见


async def test_group_events_list(require_db, client):
    """群组组队列表：成员可见全部状态，非成员 403。"""
    group_id, token_a, _ = await _group_with_second(client, "ev_gl_a", "ev_gl_b")
    event1 = await _create_event(client, token_a, group_id)
    event2 = await _create_event(client, token_a, group_id)
    await client.post(f"{EVENTS_URL}/events/{event2['id']}/cancel", headers=_auth(token_a))

    # 成员可见（含已取消的全状态）
    token_b, _ = await _login(client, "ev_gl_b")
    resp = await client.get(
        f"{EVENTS_URL}/groups/{group_id}/events", headers=_auth(token_b)
    )
    assert resp.status_code == 200
    events = resp.json()
    ids = {e["id"] for e in events}
    assert event1["id"] in ids and event2["id"] in ids
    statuses = {e["id"]: e["status"] for e in events}
    assert statuses[event2["id"]] == "CANCELLED"

    # 非成员不可见
    outsider, _ = await _login(client, "ev_gl_x")
    resp = await client.get(
        f"{EVENTS_URL}/groups/{group_id}/events", headers=_auth(outsider)
    )
    assert resp.status_code == 403


# ---------- 加入 / 重复 / 满员 ----------


async def test_join_event_and_members(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_j_a", "ev_j_b")
    event = await _create_event(client, token_a, group_id)
    token_b, _ = await _login(client, "ev_j_b")

    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 200
    assert resp.json()["current_members"] == 2

    members = (
        await client.get(
            f"{EVENTS_URL}/events/{event['id']}/members", headers=_auth(token_a)
        )
    ).json()
    assert len(members) == 2


async def test_join_duplicate_conflict(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_d_a", "ev_d_b")
    event = await _create_event(client, token_a, group_id)
    token_b, _ = await _login(client, "ev_d_b")
    await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b))
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 409


async def test_join_when_full_409(require_db, client):
    group_id, token_a, invite_code = await _group_with_second(client, "ev_f_a", "ev_f_b")
    event = await _create_event(client, token_a, group_id, max_members=2)
    token_b, _ = await _login(client, "ev_f_b")
    await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b))
    # 已满 2/2
    token_c = await _add_member(client, invite_code, "ev_f_c")
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_c)
    )
    assert resp.status_code == 409
    # 满员后状态为 CONFIRMED
    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["status"] == "CONFIRMED"
    assert detail["current_members"] == 2


async def test_join_non_group_member_404(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_p_a", "ev_p_b")
    event = await _create_event(client, token_a, group_id)
    outsider, _ = await _login(client, "ev_p_x")
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(outsider)
    )
    assert resp.status_code == 404


async def test_concurrent_join_no_overflow(require_db, client):
    """并发核心用例：max=6 当前 5，两人同时加入，最终恰好 6，绝不超员。"""
    group_id, token_a, invite_code = await _group_with_second(client, "ev_cc_a", "ev_cc_b")
    event = await _create_event(client, token_a, group_id, max_members=6)
    # A(创建者) + B..E = 5 人
    token_b, _ = await _login(client, "ev_cc_b")  # B 已是群成员
    tokens = [token_b]
    for code in ("ev_cc_c", "ev_cc_d", "ev_cc_e"):
        tokens.append(await _add_member(client, invite_code, code))
    for t in tokens:
        await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(t))

    token_f = await _add_member(client, invite_code, "ev_cc_f")
    token_g = await _add_member(client, invite_code, "ev_cc_g")

    r1, r2 = await asyncio.gather(
        client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_f)),
        client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_g)),
    )
    codes = sorted([r1.status_code, r2.status_code])
    assert codes == [200, 409], f"并发加入结果异常: {codes}"

    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["current_members"] == 6
    assert detail["status"] == "CONFIRMED"


# ---------- 退出 ----------


async def test_leave_and_rejoin(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_l_a", "ev_l_b")
    event = await _create_event(client, token_a, group_id)
    token_b, _ = await _login(client, "ev_l_b")
    await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b))

    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/leave", headers=_auth(token_b)
    )
    assert resp.status_code == 204
    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["current_members"] == 1

    # 退出后可重新加入
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 200
    assert resp.json()["current_members"] == 2


async def test_leave_when_not_joined_404(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_nj_a", "ev_nj_b")
    event = await _create_event(client, token_a, group_id)
    outsider, _ = await _login(client, "ev_nj_x")
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/leave", headers=_auth(outsider)
    )
    assert resp.status_code == 404


async def test_concurrent_leave_no_error(require_db, client):
    """两个成员同时退出：行锁串行化处理，均成功且人数正确（§40 多人同时退出）。"""
    group_id, token_a, invite_code = await _group_with_second(
        client, "ev_clv_a", "ev_clv_b"
    )
    event = await _create_event(client, token_a, group_id, max_members=6)
    token_b, _ = await _login(client, "ev_clv_b")  # B 已是群成员
    token_c = await _add_member(client, invite_code, "ev_clv_c")
    for t in (token_b, token_c):
        await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(t))

    r1, r2 = await asyncio.gather(
        client.post(f"{EVENTS_URL}/events/{event['id']}/leave", headers=_auth(token_b)),
        client.post(f"{EVENTS_URL}/events/{event['id']}/leave", headers=_auth(token_c)),
    )
    assert r1.status_code == 204 and r2.status_code == 204

    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["current_members"] == 1  # 只剩创建者


# ---------- 状态流转 ----------


async def test_status_flow_confirmed_completed(require_db, client):
    group_id, token_a, invite_code = await _group_with_second(client, "ev_sf_a", "ev_sf_b")
    event = await _create_event(client, token_a, group_id, max_members=2)
    token_b, _ = await _login(client, "ev_sf_b")
    await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b))

    # 满员 → CONFIRMED
    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["status"] == "CONFIRMED"

    # 有人退出 → 回到 RECRUITING
    await client.post(f"{EVENTS_URL}/events/{event['id']}/leave", headers=_auth(token_b))
    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["status"] == "RECRUITING"

    # 再次加入后由创建者完成
    await client.post(f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b))
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/complete", headers=_auth(token_a)
    )
    assert resp.status_code == 204
    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["status"] == "COMPLETED"

    # 完成后不能加入
    token_c = await _add_member(client, invite_code, "ev_sf_c")
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_c)
    )
    assert resp.status_code == 400


async def test_cancel_and_permission(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_cl_a", "ev_cl_b")
    event = await _create_event(client, token_a, group_id)

    # 非创建者不能完成/取消
    token_b, _ = await _login(client, "ev_cl_b")
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/complete", headers=_auth(token_b)
    )
    assert resp.status_code == 403
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/cancel", headers=_auth(token_b)
    )
    assert resp.status_code == 403

    # 创建者取消
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/cancel", headers=_auth(token_a)
    )
    assert resp.status_code == 204
    detail = (
        await client.get(f"{EVENTS_URL}/events/{event['id']}", headers=_auth(token_a))
    ).json()
    assert detail["status"] == "CANCELLED"

    # 已取消不能再加入/退出
    resp = await client.post(
        f"{EVENTS_URL}/events/{event['id']}/join", headers=_auth(token_b)
    )
    assert resp.status_code == 400


# ---------- 我的组队列表 ----------


async def test_my_events_requires_auth(client):
    resp = await client.get(f"{EVENTS_URL}/events/mine")
    assert resp.status_code == 401


async def test_my_events_list(require_db, client):
    group_id, token_a, invite_code = await _group_with_second(
        client, "ev_mine_a", "ev_mine_b"
    )
    event1 = await _create_event(client, token_a, group_id)
    event2 = await _create_event(client, token_a, group_id)

    token_b, _ = await _login(client, "ev_mine_b")
    await client.post(f"{EVENTS_URL}/events/{event1['id']}/join", headers=_auth(token_b))

    mine_a = (
        await client.get(f"{EVENTS_URL}/events/mine", headers=_auth(token_a))
    ).json()
    mine_b = (
        await client.get(f"{EVENTS_URL}/events/mine", headers=_auth(token_b))
    ).json()

    ids_a = {e["id"] for e in mine_a}
    ids_b = {e["id"] for e in mine_b}
    # A 创建了两个组队（创建者自动入队），B 只加入第一个
    assert event1["id"] in ids_a and event2["id"] in ids_a
    assert event1["id"] in ids_b and event2["id"] not in ids_b

    # 字段完整（人数/状态/餐厅）
    first = next(e for e in mine_a if e["id"] == event1["id"])
    assert first["current_members"] >= 1
    assert first["status"] == "RECRUITING"
    assert "restaurant" in first


# ---------- 权限 ----------


async def test_event_detail_non_group_member_404(require_db, client):
    group_id, token_a , _ic = await _group_with_second(client, "ev_da_a", "ev_da_b")
    event = await _create_event(client, token_a, group_id)
    outsider, _ = await _login(client, "ev_da_x")
    resp = await client.get(
        f"{EVENTS_URL}/events/{event['id']}", headers=_auth(outsider)
    )
    assert resp.status_code == 404
    resp = await client.get(
        f"{EVENTS_URL}/events/{event['id']}/members", headers=_auth(outsider)
    )
    assert resp.status_code == 404
