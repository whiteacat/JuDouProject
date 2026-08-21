"""评价与群组餐厅库接口测试（mock 高德 + 真实数据库）。

覆盖：评价资格、每人一次、非成员拒绝、无餐厅拒绝、聚合评分（§38 验收）、
群餐厅库入库与统计、评价列表。
"""

import datetime as dt

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


async def _group(client, code_a: str, code_b: str) -> tuple[int, str, str]:
    token_a, _ = await _login(client, code_a)
    group = (
        await client.post(
            f"{BASE}/groups", json={"name": "评价测试群"}, headers=_auth(token_a)
        )
    ).json()
    token_b, _ = await _login(client, code_b)
    await client.post(
        f"{BASE}/groups/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    return group["id"], token_a, group["invite_code"]


async def _add_member(client, invite_code: str, code: str) -> str:
    token, _ = await _login(client, code)
    await client.post(
        f"{BASE}/groups/join-by-code",
        json={"invite_code": invite_code},
        headers=_auth(token),
    )
    return token


async def _first_restaurant(client, token: str, keyword: str = "火锅") -> dict:
    resp = await client.get(
        f"{BASE}/restaurants/search",
        params={"keyword": keyword, "longitude": LNG, "latitude": LAT},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()[0]


async def _event_with_restaurant(
    client, token: str, group_id: int, restaurant_id: int, max_members: int = 6
) -> dict:
    resp = await client.post(
        f"{BASE}/groups/{group_id}/events",
        json={
            "title": "聚餐评价",
            "event_time": _future(),
            "min_members": 1,
            "max_members": max_members,
            "restaurant_id": restaurant_id,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _complete(client, token: str, event_id: int) -> None:
    resp = await client.post(
        f"{BASE}/events/{event_id}/complete", headers=_auth(token)
    )
    assert resp.status_code == 204, resp.text


def _payload(overall, taste, value, env, service, traffic, content="味道不错"):
    return {
        "overall_score": overall,
        "taste_score": taste,
        "value_score": value,
        "environment_score": env,
        "service_score": service,
        "traffic_score": traffic,
        "content": content,
    }


async def _review(
    client, token: str, event_id: int, scores=None, content="味道不错"
) -> dict:
    payload = scores or _payload(5, 5, 5, 5, 5, 5, content)
    resp = await client.post(
        f"{BASE}/events/{event_id}/reviews",
        json=payload,
        headers=_auth(token),
    )
    return resp


# ---------- 评价资格 ----------


async def test_review_requires_auth(client):
    resp = await client.post(f"{BASE}/events/1/reviews", json=_payload(5, 5, 5, 5, 5, 5))
    assert resp.status_code == 401


async def test_review_not_completed_400(require_db, client):
    group_id, token_a, _ = await _group(client, "rv_nc_a", "rv_nc_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)

    resp = await _review(client, token_a, event["id"])
    assert resp.status_code == 400  # 尚未完成


async def test_review_member_only(require_db, client):
    group_id, token_a, invite_code = await _group(client, "rv_mo_a", "rv_mo_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])

    # 群成员但未加入组队 → 403
    token_b, _ = await _login(client, "rv_mo_b")
    resp = await _review(client, token_b, event["id"])
    assert resp.status_code == 403

    # 群外用户 → 404
    outsider, _ = await _login(client, "rv_mo_x")
    resp = await _review(client, outsider, event["id"])
    assert resp.status_code == 404


# ---------- 每人一次 / 无餐厅 ----------


async def test_review_once_per_event(require_db, client):
    group_id, token_a, _ = await _group(client, "rv_once_a", "rv_once_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])

    resp = await _review(client, token_a, event["id"])
    assert resp.status_code == 201, resp.text

    resp = await _review(client, token_a, event["id"], _payload(4, 4, 4, 4, 4, 4))
    assert resp.status_code == 409  # 每人一次


async def test_review_without_restaurant_400(require_db, client):
    group_id, token_a, _ = await _group(client, "rv_nr_a", "rv_nr_b")
    # 不指定餐厅，仅带坐标
    resp = await client.post(
        f"{BASE}/groups/{group_id}/events",
        json={
            "title": "无餐厅聚餐",
            "event_time": _future(),
            "min_members": 1,
            "max_members": 4,
            "latitude": LAT,
            "longitude": LNG,
        },
        headers=_auth(token_a),
    )
    event = resp.json()
    await _complete(client, token_a, event["id"])

    resp = await _review(client, token_a, event["id"])
    assert resp.status_code == 400  # 无餐厅不可评价


async def test_overall_computed_from_five_dims(require_db, client):
    """客户端即使提交 overall_score 也被忽略，总分由五维加权计算。"""
    group_id, token_a, _ = await _group(client, "rv_oc_a", "rv_oc_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])

    # overall 提交 1，五维全 5 → 总分应为 5.0（而非 1）
    resp = await _review(
        client, token_a, event["id"], _payload(1, 5, 5, 5, 5, 5, "总分由五维计算")
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["overall_score"] == 5.0


# ---------- 聚合评分（§38 验收） ----------


async def test_aggregate_score_correct(require_db, client):
    group_id, token_a, invite_code = await _group(client, "rv_agg_a", "rv_agg_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid, max_members=4)

    # B/C/D 入群并入队，凑齐 4 人
    for code in ("rv_agg_b", "rv_agg_c", "rv_agg_d"):
        t = await _add_member(client, invite_code, code)
        await client.post(f"{BASE}/events/{event['id']}/join", headers=_auth(t))
    await _complete(client, token_a, event["id"])

    # 4 人 4 评价（六维各不相同）
    reviews = [
        ("rv_agg_a", 5, 5, 4, 4, 3, 3),
        ("rv_agg_b", 4, 3, 5, 2, 4, 5),
        ("rv_agg_c", 3, 4, 3, 5, 2, 4),
        ("rv_agg_d", 4, 4, 4, 4, 4, 4),
    ]
    for code, o, t, v, e, s, tr in reviews:
        tkn, _ = await _login(client, code)
        resp = await _review(client, tkn, event["id"], _payload(o, t, v, e, s, tr))
        assert resp.status_code == 201, resp.text

    from app.services.review_service import compute_overall_score

    # 总分 = 五维加权（与后端同一函数）；其余五维断言保持 AVG
    expected_overalls = [
        compute_overall_score(
            {
                "taste_score": t,
                "value_score": v,
                "environment_score": e,
                "service_score": s,
                "traffic_score": tr,
            }
        )
        for _, _o, t, v, e, s, tr in reviews
    ]
    expected_score = round(sum(expected_overalls) / len(expected_overalls), 1)

    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants/{rid}", headers=_auth(token_a)
    )
    assert resp.status_code == 200, resp.text
    stats = resp.json()["group_stats"]
    assert stats["score"] == expected_score
    assert stats["taste"] == 4.0
    assert stats["value"] == 4.0
    assert stats["environment"] == 3.8
    assert stats["service"] == 3.2
    assert stats["traffic"] == 4.0
    assert stats["visit_count"] == 1


async def test_recompute_creates_row_with_visit_count(require_db, client):
    """旧事件（完成时未入库）评价后，recompute 重建记录的 visit_count 应等于已完成次数。"""
    from sqlalchemy import delete

    from app.db.session import async_session_factory
    from app.models.group_restaurant import GroupRestaurant

    group_id, token_a, _ = await _group(client, "rv_rc_a", "rv_rc_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])

    # 模拟旧事件：完成时未入库（删除 record_visit 创建的记录）
    async with async_session_factory() as db:
        await db.execute(
            delete(GroupRestaurant).where(
                GroupRestaurant.group_id == group_id,
                GroupRestaurant.restaurant_id == rid,
            )
        )
        await db.commit()

    # 评价 → recompute 重建记录
    resp = await _review(client, token_a, event["id"])
    assert resp.status_code == 201, resp.text

    # 重建后 visit_count 应为 1（该群已完成 1 次该餐厅的组队）
    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants/{rid}", headers=_auth(token_a)
    )
    assert resp.status_code == 200
    assert resp.json()["group_stats"]["visit_count"] == 1


# ---------- 我的评价 ----------


async def test_my_reviews_requires_auth(client):
    resp = await client.get(f"{BASE}/users/me/reviews")
    assert resp.status_code == 401


async def test_my_reviews_list(require_db, client):
    import uuid

    # 每次运行使用唯一 code，避免固定 code 跨运行计数累加
    code = f"mr_{uuid.uuid4().hex[:8]}"
    group_id, token_a, _ = await _group(client, code, f"{code}_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])
    await _review(client, token_a, event["id"], _payload(5, 5, 4, 4, 4, 4, "好吃"))

    resp = await client.get(f"{BASE}/users/me/reviews", headers=_auth(token_a))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert item["restaurant_id"] == rid
    assert item["restaurant_name"]
    assert item["group_id"] == group_id
    assert item["event_id"] == event["id"]
    # 总分 = 五维加权：(口味5, 性价比4, 环境4, 服务4, 交通4) → 4.3
    assert item["overall_score"] == 4.3
    assert item["content"] == "好吃"

    # 未评价的用户列表为空
    token_b, _ = await _login(client, f"{code}_b")
    resp = await client.get(f"{BASE}/users/me/reviews", headers=_auth(token_b))
    assert resp.json() == []


# ---------- 用户统计 ----------


async def test_my_stats_requires_auth(client):
    resp = await client.get(f"{BASE}/users/me/stats")
    assert resp.status_code == 401


async def test_my_stats_counts(require_db, client):
    import uuid

    # 每次运行使用唯一 code：mock 用户按 openid 幂等 upsert，固定 code 会让计数跨运行累加
    code = f"st_{uuid.uuid4().hex[:8]}"
    group_id, token_a, _ = await _group(client, code, f"{code}_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])
    await _review(client, token_a, event["id"])

    resp = await client.get(f"{BASE}/users/me/stats", headers=_auth(token_a))
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["group_count"] == 1
    assert stats["event_count"] == 1  # 创建者自动入队
    assert stats["review_count"] == 1


# ---------- 群餐厅库 ----------


async def test_complete_adds_to_library(require_db, client):
    group_id, token_a, _ = await _group(client, "rv_lib_a", "rv_lib_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)
    await _complete(client, token_a, event["id"])

    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants", headers=_auth(token_a)
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    target = next(i for i in items if i["restaurant"]["id"] == rid)
    assert target["group_stats"]["visit_count"] == 1


async def test_group_restaurant_never_visited(require_db, client):
    group_id, token_a, _ = await _group(client, "rv_nv_a", "rv_nv_b")
    rid2 = (await _first_restaurant(client, token_a, keyword="烧烤"))["id"]

    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants/{rid2}", headers=_auth(token_a)
    )
    assert resp.status_code == 200
    stats = resp.json()["group_stats"]
    assert stats["visit_count"] == 0
    assert stats["score"] is None


async def test_group_restaurants_member_only(require_db, client):
    group_id, token_a, _ = await _group(client, "rv_gm_a", "rv_gm_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    outsider, _ = await _login(client, "rv_gm_x")

    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants", headers=_auth(outsider)
    )
    assert resp.status_code == 404
    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants/{rid}", headers=_auth(outsider)
    )
    assert resp.status_code == 404


async def test_review_lists(require_db, client):
    group_id, token_a, invite_code = await _group(client, "rv_lst_a", "rv_lst_b")
    rid = (await _first_restaurant(client, token_a))["id"]
    event = await _event_with_restaurant(client, token_a, group_id, rid)

    token_b, _ = await _login(client, "rv_lst_b")
    await client.post(f"{BASE}/events/{event['id']}/join", headers=_auth(token_b))
    await _complete(client, token_a, event["id"])

    for tkn in (token_a, token_b):
        resp = await _review(client, tkn, event["id"], _payload(5, 5, 4, 5, 4, 4))
        assert resp.status_code == 201, resp.text

    # 餐厅全部评价
    resp = await client.get(f"{BASE}/restaurants/{rid}/reviews", headers=_auth(token_a))
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
    assert all("nickname" in r for r in resp.json())

    # 群内评价
    resp = await client.get(
        f"{BASE}/groups/{group_id}/restaurants/{rid}/reviews", headers=_auth(token_a)
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2
