"""登录与用户接口测试（mock 微信模式 + 真实数据库）。

覆盖：登录创建用户、upsert 幂等、多用户区分、参数校验、401、/users/me。
"""

LOGIN_URL = "/api/v1/auth/wechat/login"
ME_URL = "/api/v1/users/me"


async def _login(client, code: str):
    resp = await client.post(LOGIN_URL, json={"code": code})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_login_creates_user(require_db, client):
    body = await _login(client, "alice")
    assert body["access_token"]
    assert isinstance(body["user"]["id"], int)
    assert body["user"]["nickname"] == "微信用户"
    assert isinstance(body["user"]["avatar_url"], str)


async def test_login_upsert_idempotent(require_db, client):
    first = await _login(client, "bob")
    second = await _login(client, "bob")
    assert first["user"]["id"] == second["user"]["id"]
    assert first["access_token"] != second["access_token"]  # 每次登录签发新 token


async def test_login_distinct_users(require_db, client):
    alice = await _login(client, "carol")
    bob = await _login(client, "dave")
    assert alice["user"]["id"] != bob["user"]["id"]


async def test_login_empty_code_rejected(require_db, client):
    resp = await client.post(LOGIN_URL, json={"code": ""})
    assert resp.status_code == 422


async def test_me_requires_token(client):
    resp = await client.get(ME_URL)
    assert resp.status_code == 401


async def test_me_rejects_invalid_token(client):
    resp = await client.get(ME_URL, headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


async def test_me_with_valid_token(require_db, client):
    body = await _login(client, "erin")
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert resp.status_code == 200
    me = resp.json()
    assert me["id"] == body["user"]["id"]
    assert me["nickname"] == body["user"]["nickname"]
