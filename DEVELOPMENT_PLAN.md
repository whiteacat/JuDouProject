# 开发计划：群组聚餐组队微信小程序 MVP

> 依据 `Architect&Plan.md` 制定。本文件是可执行的任务计划；文档中的设计约束为硬性输入（§13-21 API、§27 状态机、§28 业务规则、§5-12 数据模型、§32-42 阶段划分），此处只做定案与任务拆解，不再重复论证。

## 1. 定案摘要

| 项 | 定案 |
|---|---|
| 核心闭环 | 群组 → 组队 → 地图 → 聚餐 → 评价 → 群组餐厅库 → 再组队 |
| 核心领域模型 | `Group`、`GroupEvent`、`Restaurant`、`Review`（+ `GroupRestaurant` 聚合） |
| MVP 明确不做 | 账单分摊 / AA / 支付 / 团购 / AI / 好友系统 / 商家端（数据库预留扩展字段） |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| 数据库 | PostgreSQL 16 + PostGIS（`location` GEOMETRY(Point) + GIST 索引） |
| 缓存 | Redis（MVP 用于 token/限流，业务不强依赖） |
| 小程序 | 微信原生 + TypeScript（已确认） |
| 地图 | 高德 POI，**后端代理**（小程序 → 后端 → 高德，前端不直连第三方） |
| 鉴权 | 微信 `code2session` → 自签 JWT（`access_token`） |
| 本地环境 | Docker Compose（postgis/postgres、redis、backend） |
| API 文档 | OpenAPI / Swagger 自动生成 |

## 2. 仓库结构

```text
judouproject/
├── Architect&Plan.md        # 架构设计（只读基准）
├── DEVELOPMENT_PLAN.md      # 本开发计划
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # config / security(JWT) / deps(当前用户)
│   │   ├── db/              # async session、init_db
│   │   ├── models/          # SQLAlchemy 模型（按领域分文件）
│   │   ├── schemas/         # Pydantic 请求/响应
│   │   ├── api/v1/          # auth, users, groups, events, restaurants, reviews
│   │   └── services/        # 业务逻辑：状态机、聚合评分、并发控制
│   ├── alembic/             # 数据库迁移
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── miniprogram/             # 微信小程序（原生 + TS）
│   ├── app.ts / app.json / app.wxss
│   ├── pages/               # index, group/*, event/*, restaurant/*, user/*
│   ├── components/          # MapContainer, EventMarker, EventBottomSheet 等
│   └── utils/               # request(带 token)、auth、location
└── deploy/
    ├── docker-compose.yml   # postgres(postgis), redis, backend
    └── .env.example
```

## 3. 里程碑总览

| 里程碑 | 内容 | 对应文档 | 依赖 | 验收一句话 |
|---|---|---|---|---|
| M0 | 项目基础设施 | §32 Phase 0 | — | 后端可跑、可连库、健康检查通过 |
| M1 | 用户系统 + 微信登录 | §14 | M0 | 两个用户可登录并获得 JWT |
| M2 | 群组系统 | §15 | M1 | 两个用户进同一群并互相可见 |
| M3 | 地图 + 餐厅（高德 POI） | §17/§19/§34 | M2 | 地图上能搜到餐厅并查看详情 |
| M4 | 组队系统（状态机 + 并发） | §16-18/§27-29 | M2(+M3) | A 建队、B 地图看到、C 加入，三方状态一致 |
| M5 | 微信分享 | §36 | M4 | A 分享 → B 点开 → 查看 → 加入 |
| M6 | 群组餐厅库 + 评价 | §20-21/§37-38 | M4 | 4 人 4 评，群组评分自动聚合 |
| M7 | MVP 联调闭环 | §39 | M1-M6 | 登录→建群→组队→聚餐→评价→再组队全通 |
| M8 | 测试加固 + 上线准备 | §40 | M7 | 核心并发/边界用例全绿，可灰度 |

## 4. M0 项目基础设施

目标：项目能运行，前后端能通信，数据库能连接。

任务：
1. git 仓库初始化 + `.gitignore`（backend / miniprogram / deploy）
2. `deploy/docker-compose.yml`：`postgis/postgis:16-3.4`、`redis:7`、backend 服务
3. backend 骨架：FastAPI 应用、`GET /api/v1/health`（含 DB SELECT 1）、配置中心（pydantic-settings）、基础日志
4. SQLAlchemy async 引擎 + session 依赖 + Alembic 初始化
5. `pyproject.toml` 依赖锁定；本地启动脚本（`make dev` / 等效）
6. CI：GitHub Actions（lint + pytest + docker build）
7. 小程序骨架：`app.json`、tabBar（地图 / 群组 / 我的）、request 工具（带 baseURL 配置）、登录页占位

验收：
- `docker compose up` 后 `GET /api/v1/health` 返回 ok，后端能连上 PG + PostGIS（`SELECT postgis_version()`）
- 小程序 devtools 能编译并请求本地后端（含合法域名/代理说明）

## 5. M1 用户系统（§14）

任务：
1. `users` 表 + 模型（openid UNIQUE、unionid NULL、nickname、avatar_url、status、时间戳）
2. `POST /auth/wechat/login`：code → 微信 code2session（appid/secret 走环境变量；无 appid 时提供 **mock 登录模式**）→ upsert 用户 → 签发 JWT
3. `GET /users/me`：当前用户信息（JWT → DB）
4. 小程序：`wx.login` 静默登录 → 换 token 存 storage → 请求拦截器自动携带 `Authorization`
5. 单元测试：登录 upsert 幂等、无效 code、无 token 访问受保护接口返回 401

验收：两个微信用户各自登录后都能拿到 JWT，`/users/me` 返回各自资料。

## 6. M2 群组系统（§15、§5.2/5.3）

任务：
1. `groups`、`group_members` 表 + 模型（UNIQUE(group_id, user_id)；role：OWNER/ADMIN/MEMBER）
2. `POST /groups`：创建群组（创建者自动 OWNER，生成唯一邀请码）
3. `GET /groups` 我的群组列表；`GET /groups/{id}` 详情
4. `POST /groups/join-by-code`：邀请码加入
5. `GET /groups/{id}/members`；`POST /groups/{id}/leave`（普通成员退出；OWNER 不允许直接退出）
6. `POST /groups/{id}/transfer`：转让群主给群内其他成员（OWNER 退出的前置步骤，转让后原 OWNER 可正常退出）
7. 小程序：群组列表页、创建页、加入页、群组主页（成员头像、餐厅库入口、发起组队入口）

验收：A 建群拿到邀请码 → B 输码加入 → 双方群组主页互相可见。

## 7. M3 地图 + 餐厅（§17、§19、§34）

任务：
1. `restaurants` 表 + 模型（location GEOMETRY(Point) + GIST 索引、source/source_id UNIQUE、status）
2. `GET /restaurants/search`：keyword/lng/lat/radius/category → 后端调高德 POI → 标准化落库（已存在则复用）
3. `GET /restaurants/{id}`：详情
4. 小程序：地图页（`wx.getLocation` 授权 → MapContainer → 搜索结果 Marker → 餐厅详情弹层）
5. 配置：高德 Web 服务 Key 走环境变量；无 key 时 mock POI 供开发

验收：用户在地图当前视野内搜索"火锅"，出现餐厅 Marker，点击可看名称/地址/评分等基本信息。

## 8. M4 组队系统（§16-18、§27-29、§41）★ 核心里程碑

任务：
1. `group_events`（restaurant_id/lat/lng 可空；预留 total_amount 字段不启用）、`event_members`（UNIQUE(event_id, user_id)）表 + 模型
2. `POST /groups/{id}/events`：创建（校验本组成员、时间合理、min≤max；可选餐厅）
3. `GET /groups/{id}/events/map`：center+radius / bbox 过滤、status 与时间过滤，返回事件 + 餐厅坐标 + 当前人数（§17 响应结构）
4. `POST /events/{id}/join`：**并发安全**（行锁 `SELECT ... FOR UPDATE` + 计数校验 < max_members；UNIQUE 约束兜底重复加入）→ 满员自动 RECRUITING→CONFIRMED
5. `POST /events/{id}/leave`：状态校验（仅 RECRUITING/CONFIRMED 可退）
6. `POST /events/{id}/complete`、`POST /events/{id}/cancel`：状态机后端统一控制（§27）
7. `GET /events/{id}`、`GET /events/{id}/members`
8. 小程序：组队创建页（时间/人数/备注/选餐厅）、地图 Marker + 底部弹层（详情/加入）、组队详情页（成员列表/状态/操作栏）

验收（§35）：
- A 建队（max=6）→ B 地图看到 Marker → C 点开加入 → A/B/C 成员与状态一致
- 并发用例：max=6 当前 5，A、B 同时 join，最终恰好 6，绝不超员

## 9. M5 微信分享（§36）

任务：
1. 群组分享：`onShareAppMessage` 携带 group_id，落地页 = 群组主页
2. 组队分享：携带 event_id，落地页 = 组队详情页（未登录 → 先登录 → 查看 → 加入）
3. 分享参数校验（不存在/无权限给友好提示）

验收：A 创建组队 → 分享到微信群 → B 点开进入小程序 → 看到组队 → 加入成功。这是 MVP 重点测试场景。

## 10. M6 群组餐厅库 + 评价系统（§20-21、§37-38）

任务：
1. `reviews` 表（UNIQUE(event_id, user_id)）+ 模型
2. `POST /events/{id}/reviews`：校验（EventMember.status=JOINED、事件 COMPLETED、每人一次）→ 写 review 后**事务内重算** `group_restaurants` 聚合分（§12 简单平均）
3. 事件完成时（或查询兜底）将餐厅 upsert 进 `group_restaurants`（visit_count+1、last_visit_at）
4. `GET /groups/{id}/restaurants`；`GET /groups/{id}/restaurants/{rid}`（返回 group_stats，§20）；`GET /restaurants/{rid}/reviews`；`GET /groups/{id}/restaurants/{rid}/reviews`
5. 小程序：评价页（六维评分 + 文字）、餐厅详情页（群评分展示，§26 样式）、群组餐厅库列表

验收（§38）：4 人聚餐完成 → 4 人各评价一次 → 群组评分 = 简单平均正确；第 5 次评价被拒；非成员评价被拒。

## 11. M7 联调闭环 + M8 测试与上线

### M7（§39）
完整走查：登录 → 建群 → 邀请 → 地图 → 找餐厅 → 组队 → 分享 → 加入 → 完成 → 评价 → 群组库 → 再组队；修复跨端问题；补齐异常路径（取消、满员、过期）。闭环跑通即 MVP 成立。

### M8（§40）
- 测试矩阵：多人同时加入/退出、达上限、重复加入、取消、完成、重复评价、非成员评价、群组切换、分享链接
- 并发测试：pytest 并发 join 断言不超员（§40.1）
- 上线准备：HTTPS 合法域名配置、正式 AppID、高德 key 权限、日志监控（Loki 可后置）、体验版灰度

## 12. 数据库与 API 落地顺序

| 里程碑 | 建表 | 新增 API |
|---|---|---|
| M0 | — | `GET /api/v1/health` |
| M1 | users | `POST /auth/wechat/login`、`GET /users/me` |
| M2 | groups, group_members | `POST /groups`、`GET /groups`、`GET /groups/{id}`、`POST /groups/join-by-code`、`GET /groups/{id}/members`、`POST /groups/{id}/transfer`、`POST /groups/{id}/leave` |
| M3 | restaurants | `GET /restaurants/search`、`GET /restaurants/{id}` |
| M4 | group_events, event_members | `POST /groups/{id}/events`、`GET /groups/{id}/events/map`、`POST /events/{id}/join|leave|complete|cancel`、`GET /events/{id}`、`GET /events/{id}/members` |
| M6 | reviews, group_restaurants | `POST /events/{id}/reviews`、`GET /groups/{id}/restaurants`、`GET /groups/{id}/restaurants/{rid}`、`GET /restaurants/{rid}/reviews` |

## 13. 关键业务规则实现清单（§28）

- [ ] 人数上限：join 行锁 + 计数校验，超员返回 409
- [ ] 重复加入：DB UNIQUE 约束 + 应用层友好报错
- [ ] COMPLETED / CANCELLED 后禁止加入、退出
- [ ] 满员自动 CONFIRMED（join 事务内更新状态）
- [ ] 评价资格：仅 JOINED 成员 + 事件 COMPLETED + UNIQUE(event_id, user_id)
- [ ] 聚合评分：review 写入后事务内重算（幂等、可重跑）
- [ ] 邀请码唯一 + 群组 status 校验
- [ ] 转让群主：仅 OWNER 可发起，接收人须为群内成员；转让后原 OWNER 可退出，接收人成为新 OWNER

## 14. 风险与前置依赖

| 风险 / 依赖 | 对策 |
|---|---|
| 微信 AppID 未申请 | M1 提供 mock 登录模式，开发不受阻 |
| 高德 Key / 配额 | M3 提供 mock POI；Key 走环境变量 |
| 小程序地图组件与定位权限 | 提前真机验证 `wx.getLocation` + map 组件 |
| PostGIS 本地安装困难 | Docker 镜像自带 postgis，避免本机安装 |
| 并发超员 | M4 必须实现行锁 + 并发测试（§40） |
| 分享落地页登录态 | M5 统一处理未登录跳转 |

## 15. 已确认决定

1. **小程序框架**：微信原生 + TypeScript（已确认，2026-08-19）
2. **OWNER 退出规则**：不允许直接退出，需先通过 `POST /groups/{id}/transfer` 将群主转让给群内成员（已确认，2026-08-19）
