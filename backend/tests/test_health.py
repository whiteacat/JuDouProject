"""health 接口测试：不依赖真实数据库，通过依赖覆盖注入 fake session。"""

from app.db.session import get_db


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeDB:
    """模拟 AsyncSession.execute：首次 SELECT 1，第二次查询 postgis 版本。"""

    def __init__(self, db_ok: bool = True, postgis_version: str = "3.4.0"):
        self.db_ok = db_ok
        self.postgis_version = postgis_version
        self.calls = 0

    async def execute(self, _stmt):
        self.calls += 1
        if not self.db_ok:
            raise RuntimeError("database unavailable")
        if self.calls == 1:
            return _Result(None)
        return _Result(self.postgis_version)


def _override(fake: _FakeDB):
    async def _get_db():
        yield fake

    from app.main import app

    app.dependency_overrides[get_db] = _get_db
    return app


async def test_health_ok(client):
    app = _override(_FakeDB(db_ok=True, postgis_version="3.4.0"))
    resp = await client.get("/api/v1/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["postgis"] == "3.4.0"


async def test_health_degraded(client):
    app = _override(_FakeDB(db_ok=False))
    resp = await client.get("/api/v1/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["db"] is False
    assert body["postgis"] is None


async def test_unknown_route_returns_404(client):
    resp = await client.get("/api/v1/not-exist")
    assert resp.status_code == 404


async def test_health_module_router_registered():
    # 保证 health 路由被聚合进 v1 路由
    from app.api.v1.router import api_router

    routes = {getattr(r, "path", None) for r in api_router.routes}
    assert "/health" in routes
