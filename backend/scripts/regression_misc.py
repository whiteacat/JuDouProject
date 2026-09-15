"""收藏/评价/通知/反馈/管理开关 域回归脚本（backend 容器内运行）"""
import asyncio

import httpx

BASE = "http://localhost:8000/api/v1"
T1 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwianRpIjoiMjc5MmE0MGEtMjk2Yi00OGQxLTk5ODAtZjgyNTRhZmM1MzFiIiwiaWF0IjoxNzg5MzczNjMyLCJleHAiOjE3ODk5Nzg0MzJ9.1pVV7EGZ5jMbGxqsxxhDUIhxodco6cRo2c_x6mZxB18"
T2 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwianRpIjoiMzNkNWI4NjAtMzMzZS00NmYzLTljMjQtZTlmM2RmN2VkZTg1IiwiaWF0IjoxNzg5MzczNjMyLCJleHAiOjE3ODk5Nzg0MzJ9.ldcgpqO5xUJAf8AbhMcF2ZFQULvVjm9lhxom0IY84Oo"
GID = 4

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + (" " + str(extra)[:160] if extra else ""))


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        h1 = {"Authorization": f"Bearer {T1}"}
        h2 = {"Authorization": f"Bearer {T2}"}

        # ---- 准备：建一个指定餐厅的活动 → 完成（供评价用）----
        r = await c.post(
            f"/groups/{GID}/events",
            headers=h1,
            json={
                "title": "回归评价链路",
                "event_time": "2026-09-27T19:00:00",
                "min_members": 1,
                "max_members": 3,
                "restaurant_id": 2,
            },
        )
        check("0a.评价链路活动创建", r.status_code == 201, f"got={r.status_code} {r.text[:100]}")
        eid = r.json().get("id")
        r = await c.post(f"/events/{eid}/join", headers=h2)
        check("0b.user2加入", r.status_code == 200, f"got={r.status_code}")
        r = await c.post(f"/events/{eid}/complete", headers=h1)
        check("0c.组织者完成", r.status_code == 204, f"got={r.status_code}")

        # ---- 评价 ----
        r = await c.post(
            f"/events/{eid}/reviews",
            headers=h2,
            json={
                "taste_score": 4.5,
                "value_score": 4,
                "environment_score": 4,
                "service_score": 5,
                "traffic_score": 4,
                "content": "回归评价测试",
            },
        )
        check("1.user2提交评价201", r.status_code == 201, f"got={r.status_code} {r.text[:120]}")
        check("1b.总分服务端加权(非0)", abs(r.json().get("overall_score", 0)) > 0, f"overall={r.json().get('overall_score')}")

        r = await c.get("/restaurants/2/reviews", headers=h2)
        rv_ids = [x["id"] for x in r.json()] if r.status_code == 200 else []
        check("2.餐厅评价列表含新评价", r.status_code == 200 and rv_ids, f"got={r.status_code} ids={rv_ids[:5]}")

        r = await c.get(f"/groups/{GID}/restaurants", headers=h2)
        glist = r.json() if r.status_code == 200 else []
        hit = [g for g in glist if g.get("restaurant", {}).get("id") == 2 or g.get("restaurant_id") == 2]
        check("3.群组餐厅库含餐厅2(visit+1)", r.status_code == 200 and hit, f"got={r.status_code} items={len(glist)}")

        # ---- 收藏 ----
        r = await c.get("/favorites", headers=h2)
        before = [f["id"] for f in r.json()] if r.status_code == 200 else []
        r = await c.put(f"/favorites/{eid}", headers=h2)
        check("4.收藏活动", r.status_code == 200, f"got={r.status_code} {r.text[:80]}")
        r = await c.get(f"/favorites/{eid}", headers=h2)
        check("4b.收藏状态查询=favorited", r.status_code == 200 and r.json().get("favorited") is True, f"got={r.text[:80]}")
        r = await c.get("/favorites", headers=h2)
        after = [f["id"] for f in r.json()] if r.status_code == 200 else []
        check("4c.收藏列表新增", r.status_code == 200 and eid in after, f"before={before[:6]} after={after[:6]}")
        r = await c.delete(f"/favorites/{eid}", headers=h2)
        check("4d.取消收藏", r.status_code == 200, f"got={r.status_code} {r.text[:80]}")

        # ---- 通知 ----
        r = await c.get("/notifications/unread-count", headers=h2)
        check("5.未读数接口200", r.status_code == 200, f"got={r.status_code} {r.text[:80]}")
        unread = r.json().get("unread_count")
        r = await c.get("/notifications", headers=h2)
        items = r.json().get("items", []) if r.status_code == 200 and isinstance(r.json(), dict) else (r.json() if r.status_code == 200 else [])
        check("6.通知列表200(含事件通知)", r.status_code == 200 and len(items) >= 1, f"got={r.status_code} n={len(items)}")
        if items:
            nid = items[0].get("id")
            r = await c.post(f"/notifications/{nid}/read", headers=h2)
            check("7.标记单条已读204", r.status_code == 204, f"got={r.status_code}")
        r = await c.post("/notifications/read-all", headers=h2)
        check("8.全部已读204", r.status_code == 204, f"got={r.status_code}")
        r = await c.get("/notifications/unread-count", headers=h2)
        check("8b.全部已读后count=0", r.json().get("count") == 0, f"got={r.text[:80]}")

        # ---- 反馈 ----
        r = await c.post(
            "/feedbacks",
            headers=h2,
            json={"content": "回归反馈测试内容", "kind": "suggestion", "contact": "13800000001"},
        )
        check("9.反馈提交201", r.status_code == 201, f"got={r.status_code} {r.text[:80]}")
        r = await c.post("/feedbacks", headers=h2, json={"content": "x", "kind": "hack"})
        check("9b.非法kind拒绝(400/422)", r.status_code in (400, 422), f"got={r.status_code}")

        # ---- 管理开关（服务器未配置 ADMIN_KEY → fail-closed 403）----
        r = await c.get("/admin/status")
        check("10.公开开关状态200", r.status_code == 200, f"got={r.status_code} {r.text[:80]}")
        r = await c.get("/admin/settings")
        check("11.无key读设置403(fail-closed)", r.status_code == 403, f"got={r.status_code}")
        r = await c.put("/admin/settings", json={"value": False}, headers={"X-Admin-Key": "wrong-key"})
        check("11b.错误key写设置403", r.status_code == 403, f"got={r.status_code}")

    ok = sum(1 for _, cond, _ in results if cond)
    print(f"\n==== 收藏/评价/通知/反馈/管理域回归: {ok}/{len(results)} PASS ====")
    for name, cond, extra in results:
        if not cond:
            print("FAIL:", name, str(extra)[:200])


asyncio.run(main())
