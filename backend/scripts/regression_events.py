"""活动域回归脚本（在 backend 容器内运行）：
创建/封面/预算/地点/加入退出/取消/完成/二维码/成员过滤/权限
schema: EventCreate {title, cover_url, budget, restaurant_id, event_time, min_members, max_members, latitude, longitude, remark}
"""
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

        # 1. user1 创建活动(封面+预算+手输地点，不指定餐厅 → 用手输经纬度)
        r = await c.post(
            f"/groups/{GID}/events",
            headers=h1,
            json={
                "title": "回归测试活动",
                "event_time": "2026-09-25T19:00:00",
                "min_members": 1,
                "max_members": 2,
                "cover_url": "preset://cover/03",
                "budget": 128,
                "latitude": 30.572,
                "longitude": 104.066,
                "remark": "回归",
            },
        )
        check("1.创建活动(封面/预算/手输地点)", r.status_code == 201, f"got={r.status_code} {r.text[:120]}")
        ev = r.json()
        eid = ev.get("id")
        check(
            "1b.cover/budget/手输经纬度回显",
            ev.get("cover_url") == "preset://cover/03" and ev.get("budget") == 128 and ev.get("longitude") == 104.066,
            f"cover={ev.get('cover_url')} budget={ev.get('budget')} lng={ev.get('longitude')}",
        )

        # 1c. 指定餐厅时地点应取餐厅坐标（餐厅优先于手输）
        r = await c.post(
            f"/groups/{GID}/events",
            headers=h1,
            json={
                "title": "回归餐厅坐标",
                "event_time": "2026-09-25T19:00:00",
                "min_members": 1,
                "max_members": 2,
                "restaurant_id": 2,
            },
        )
        ev1c = r.json()
        check(
            "1c.指定餐厅取餐厅坐标",
            r.status_code == 201 and abs(ev1c.get("longitude") - 116.292299) < 0.001,
            f"got={r.status_code} lng={ev1c.get('longitude')}",
        )
        if r.status_code == 201:
            # 清理该辅助活动
            await c.post(f"/events/{ev1c['id']}/cancel", headers=h1)

        # 2. 非法封面应400
        r = await c.post(
            f"/groups/{GID}/events",
            headers=h1,
            json={
                "title": "x",
                "event_time": "2026-09-25T19:00:00",
                "min_members": 1,
                "max_members": 2,
                "cover_url": "https://evil.com/a.png",
            },
        )
        check("2.非法封面400", r.status_code == 400, f"got={r.status_code}")

        # 3. user2 加入
        r = await c.post(f"/events/{eid}/join", headers=h2)
        ev = r.json() if r.content else {}
        check("3.user2加入", r.status_code == 200, f"got={r.status_code} {r.text[:100]}")
        check("3b.满员后status=CONFIRMED", ev.get("status") == "CONFIRMED", f"status={ev.get('status')}")

        # 4. user2 退出
        r = await c.post(f"/events/{eid}/leave", headers=h2)
        check("4.user2退出(204)", r.status_code == 204, f"got={r.status_code}")
        r = await c.get(f"/events/{eid}", headers=h2)
        check("4b.退出后status=RECRUITING", r.json().get("status") == "RECRUITING", f"status={r.json().get('status')}")

        # 5. user2 重复加入(名额空出)
        r = await c.post(f"/events/{eid}/join", headers=h2)
        check("5.重新加入", r.status_code == 200, f"got={r.status_code} {r.text[:80]}")

        # 6. 活动二维码返回 PNG
        r = await c.get(f"/events/{eid}/qrcode", headers=h2)
        check(
            "6.二维码PNG",
            r.status_code == 200 and r.headers.get("content-type", "").startswith("image/png") and r.content[:8] == b"\x89PNG\r\n\x1a\n",
            f"ct={r.headers.get('content-type')} len={len(r.content)}",
        )

        # 7. 我的活动(发起人)应含该活动
        r = await c.get("/events/mine", headers=h1)
        ids = [e["id"] for e in r.json()]
        check("7.events/mine含活动", eid in ids, f"ids={ids[:8]}")

        # 8. 成员可见群组活动列表
        r = await c.get(f"/groups/{GID}/events", headers=h1)
        listed = [e["id"] for e in r.json()]
        check("8.群组活动列表含活动", r.status_code == 200 and eid in listed, f"got={r.status_code} ids={listed[:8]}")

        # 9. user2(非组织者)取消应403
        r = await c.post(f"/events/{eid}/cancel", headers=h2)
        check("9.非组织者取消403", r.status_code == 403, f"got={r.status_code}")

        # 10. user1 取消活动(204)，user2 再加入应409(已取消)
        r = await c.post(f"/events/{eid}/cancel", headers=h1)
        check("10.组织者取消(204)", r.status_code == 204, f"got={r.status_code}")
        r = await c.post(f"/events/{eid}/join", headers=h2)
        check("10b.取消后加入被拒(400/409)", r.status_code in (400, 409), f"got={r.status_code} {r.text[:80]}")

        # 11. 再建一个活动走「完成」链路: 建→不加入→直接complete
        r = await c.post(
            f"/groups/{GID}/events",
            headers=h1,
            json={"title": "回归完成链路", "event_time": "2026-09-26T19:00:00", "min_members": 1, "max_members": 3},
        )
        eid2 = r.json().get("id")
        check("11a.创建完成链路活动", r.status_code == 201, f"got={r.status_code}")
        r = await c.post(f"/events/{eid2}/complete", headers=h1)
        check("11b.无参与者直接complete(204)", r.status_code == 204, f"got={r.status_code} {r.text[:100]}")
        r = await c.get(f"/events/{eid2}", headers=h1)
        check("11c.完成后status=COMPLETED", r.json().get("status") == "COMPLETED", f"status={r.json().get('status')}")

        # 12. 活动成员列表200
        r = await c.get(f"/events/{eid}/members", headers=h1)
        check("12.活动成员列表200", r.status_code == 200, f"got={r.status_code}")

    ok = sum(1 for _, cond, _ in results if cond)
    print(f"\n==== 活动域回归: {ok}/{len(results)} PASS ====")
    for name, cond, extra in results:
        if not cond:
            print("FAIL:", name, str(extra)[:200])


asyncio.run(main())
