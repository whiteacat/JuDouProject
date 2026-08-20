"""群组接口测试（mock 微信模式 + 真实数据库）。

覆盖：创建、邀请码加入、重复加入、详情权限、成员列表、退出、转让、权限校验。
"""

GROUPS_URL = "/api/v1/groups"
LOGIN_URL = "/api/v1/auth/wechat/login"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client, code: str) -> tuple[str, int]:
    resp = await client.post(LOGIN_URL, json={"code": code})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["access_token"], body["user"]["id"]


async def _create_group(client, token: str, name: str = "测试群"):
    resp = await client.post(GROUPS_URL, json={"name": name}, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_group_requires_auth(client):
    resp = await client.post(GROUPS_URL, json={"name": "x"})
    assert resp.status_code == 401


async def test_create_group(require_db, client):
    token, user_id = await _login(client, "grp_owner_a")
    group = await _create_group(client, token, "产品部")
    assert group["owner_id"] == user_id
    assert group["invite_code"] and len(group["invite_code"]) == 8
    assert group["member_count"] == 1
    assert group["name"] == "产品部"


async def test_join_by_code(require_db, client):
    token_a, _ = await _login(client, "grp_join_a")
    group = await _create_group(client, token_a)

    token_b, user_id_b = await _login(client, "grp_join_b")
    resp = await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    assert resp.status_code == 200, resp.text
    joined = resp.json()
    assert joined["id"] == group["id"]
    assert joined["member_count"] == 2
    assert joined["owner_id"] == group["owner_id"] != user_id_b


async def test_join_duplicate_conflict(require_db, client):
    token_a, _ = await _login(client, "grp_dup_a")
    group = await _create_group(client, token_a)

    token_b, _ = await _login(client, "grp_dup_b")
    await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    resp = await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    assert resp.status_code == 409


async def test_join_invalid_code(require_db, client):
    token, _ = await _login(client, "grp_badcode")
    resp = await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": "deadbeef"},
        headers=_auth(token),
    )
    assert resp.status_code == 404


async def test_group_detail_member_only(require_db, client):
    token_a, _ = await _login(client, "grp_detail_a")
    group = await _create_group(client, token_a)

    # 非成员访问返回 404（不泄露群组存在性）
    token_c, _ = await _login(client, "grp_detail_c")
    resp = await client.get(f"{GROUPS_URL}/{group['id']}", headers=_auth(token_c))
    assert resp.status_code == 404

    # 成员访问正常
    resp = await client.get(f"{GROUPS_URL}/{group['id']}", headers=_auth(token_a))
    assert resp.status_code == 200
    assert resp.json()["id"] == group["id"]


async def test_list_groups_only_mine(require_db, client):
    token_a, _ = await _login(client, "grp_list_a")
    group = await _create_group(client, token_a)

    resp = await client.get(GROUPS_URL, headers=_auth(token_a))
    assert resp.status_code == 200
    ids = [g["id"] for g in resp.json()]
    assert group["id"] in ids

    token_c, _ = await _login(client, "grp_list_c")
    resp = await client.get(GROUPS_URL, headers=_auth(token_c))
    assert group["id"] not in [g["id"] for g in resp.json()]


async def test_members_list(require_db, client):
    token_a, uid_a = await _login(client, "grp_members_a")
    group = await _create_group(client, token_a)
    token_b, uid_b = await _login(client, "grp_members_b")
    await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )

    resp = await client.get(
        f"{GROUPS_URL}/{group['id']}/members", headers=_auth(token_a)
    )
    assert resp.status_code == 200
    members = resp.json()
    roles = {m["user_id"]: m["role"] for m in members}
    assert len(members) == 2
    assert roles[uid_a] == "OWNER"
    assert roles[uid_b] == "MEMBER"


async def test_leave_group(require_db, client):
    token_a, uid_a = await _login(client, "grp_leave_a")
    group = await _create_group(client, token_a)
    token_b, _ = await _login(client, "grp_leave_b")
    await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )

    # 普通成员可退出
    resp = await client.post(f"{GROUPS_URL}/{group['id']}/leave", headers=_auth(token_b))
    assert resp.status_code == 204

    # 群主不可直接退出
    resp = await client.post(f"{GROUPS_URL}/{group['id']}/leave", headers=_auth(token_a))
    assert resp.status_code == 400


async def test_leave_then_rejoin(require_db, client):
    token_a, _ = await _login(client, "grp_rejoin_a")
    group = await _create_group(client, token_a)
    token_b, _ = await _login(client, "grp_rejoin_b")
    await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    await client.post(f"{GROUPS_URL}/{group['id']}/leave", headers=_auth(token_b))

    # 退出后可用同一邀请码重新加入（恢复身份）
    resp = await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 2


async def test_transfer_owner(require_db, client):
    token_a, uid_a = await _login(client, "grp_transfer_a")
    group = await _create_group(client, token_a)
    token_b, uid_b = await _login(client, "grp_transfer_b")
    await client.post(
        f"{GROUPS_URL}/join-by-code",
        json={"invite_code": group["invite_code"]},
        headers=_auth(token_b),
    )

    resp = await client.post(
        f"{GROUPS_URL}/{group['id']}/transfer",
        json={"user_id": uid_b},
        headers=_auth(token_a),
    )
    assert resp.status_code == 204

    # 角色互换：B 成为 OWNER，A 变为 ADMIN
    members = await client.get(
        f"{GROUPS_URL}/{group['id']}/members", headers=_auth(token_b)
    )
    roles = {m["user_id"]: m["role"] for m in members.json()}
    assert roles[uid_b] == "OWNER"
    assert roles[uid_a] == "ADMIN"

    # 详情中的 owner_id 已更新
    detail = await client.get(f"{GROUPS_URL}/{group['id']}", headers=_auth(token_b))
    assert detail.json()["owner_id"] == uid_b

    # 转让后原群主（现 ADMIN）可以退出
    resp = await client.post(f"{GROUPS_URL}/{group['id']}/leave", headers=_auth(token_a))
    assert resp.status_code == 204


async def test_transfer_permission_denied(require_db, client):
    token_a, _ = await _login(client, "grp_tperm_a")
    group = await _create_group(client, token_a)
    token_b, uid_c = await _login(client, "grp_tperm_b")

    resp = await client.post(
        f"{GROUPS_URL}/{group['id']}/transfer",
        json={"user_id": uid_c},
        headers=_auth(token_b),  # 普通用户（且不是成员）尝试转让
    )
    assert resp.status_code == 404  # 非成员视为无权访问


async def test_transfer_to_non_member(require_db, client):
    token_a, _ = await _login(client, "grp_tnm_a")
    group = await _create_group(client, token_a)
    _, uid_c = await _login(client, "grp_tnm_c")  # 未加入该群

    resp = await client.post(
        f"{GROUPS_URL}/{group['id']}/transfer",
        json={"user_id": uid_c},
        headers=_auth(token_a),
    )
    assert resp.status_code == 400


async def test_transfer_to_self(require_db, client):
    token_a, uid_a = await _login(client, "grp_tself_a")
    group = await _create_group(client, token_a)

    resp = await client.post(
        f"{GROUPS_URL}/{group['id']}/transfer",
        json={"user_id": uid_a},
        headers=_auth(token_a),
    )
    assert resp.status_code == 400
