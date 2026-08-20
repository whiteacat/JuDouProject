可以。基于前面已经确定的 MVP 范围，我建议把第一版开发目标正式收敛为：

> **以群组为核心，以地图为入口，以组队为核心行为，以群组餐厅评价库为长期数据资产。**

账单分摊暂不进入 MVP，只预留数据扩展能力。

下面我直接给你一份可以交给开发人员 / Codex / Claude Code 使用的**开发计划文档**。

# 开发计划文档：群组聚餐组队微信小程序 MVP

## 1. 项目概述

### 1.1 项目定位

开发一款基于微信小程序的多人聚餐组队工具。

核心解决：

* 群里有人想吃饭，但不知道谁参加
* 不知道去哪吃
* 无法快速查看群成员过去对餐厅的评价
* 群成员分散在不同位置，不方便确定聚餐地点
* 微信群聊天记录中的餐厅信息无法长期沉淀
* 历史聚餐经验无法形成可复用的数据

产品核心理念：

```text
群组
 ↓
组队
 ↓
地图
 ↓
聚餐
 ↓
评价
 ↓
群组餐厅知识库
 ↓
下一次组队
```

---

# 2. MVP 产品边界

## 2.1 MVP 必须实现

### 用户

* 微信登录
* 用户基本资料
* 用户所属群组
* 用户加入/退出群组

### 群组

* 创建群组
* 加入群组
* 邀请成员
* 群组成员管理
* 群组主页

### 地图

* 当前用户位置
* 地图展示
* 当前群组组队 Marker
* 点击 Marker 查看组队
* 点击组队加入

### 组队

* 创建组队
* 指定餐厅
* 不指定餐厅
* 设置时间
* 设置人数
* 设置备注
* 加入组队
* 退出组队
* 组队状态管理
* 分享组队
* 组队结束

### 餐厅

* 餐厅基础信息
* 地图位置
* 群组餐厅列表
* 历史组队次数
* 群组评价

### 评价

* 总体评分
* 口味
* 性价比
* 聚餐环境
* 服务
* 交通便利
* 文字评价
* 用户评价
* 群组聚合评分

---

# 3. MVP 暂不实现

以下功能明确从第一版排除：

```text
第三方点评平台完整评价同步
团购
在线订座
微信支付
自动分账
复杂 AA
AI 推荐
AI 评论总结
公开组队
陌生人社交
好友系统
商家端
广告
会员
```

但是数据库和 API 设计需要保证未来能够扩展。

---

# 4. 产品核心对象

整个系统围绕以下对象设计：

```text
User
 │
 ├── GroupMember
 │
 └── Review
        │
Group ──┼── GroupMember
        │
        ├── GroupRestaurant
        │
        └── GroupEvent
                │
                ├── EventMember
                │
                └── Review
                        │
                     Restaurant
```

其中：

* `User`：用户
* `Group`：群组
* `Restaurant`：标准化餐厅
* `GroupEvent`：一次组队/聚餐事件
* `Review`：用户对餐厅的评价
* `GroupRestaurant`：群组自己的餐厅库

---

# 5. 数据库 ER 模型

建议使用：

```text
PostgreSQL
+
PostGIS
```

---

## 5.1 users

```text
users
--------------------------------
id                  BIGINT PK
openid              VARCHAR UNIQUE
unionid             VARCHAR NULL
nickname            VARCHAR
avatar_url          VARCHAR
status              SMALLINT
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

---

## 5.2 groups

```text
groups
--------------------------------
id                  BIGINT PK
name                VARCHAR
avatar_url           VARCHAR
owner_id             BIGINT
invite_code          VARCHAR UNIQUE
status               SMALLINT
created_at           TIMESTAMP
updated_at           TIMESTAMP
```

---

## 5.3 group_members

```text
group_members
--------------------------------
id                  BIGINT PK
group_id            BIGINT
user_id             BIGINT
role                VARCHAR
status              SMALLINT
joined_at            TIMESTAMP
updated_at           TIMESTAMP

UNIQUE(group_id, user_id)
```

角色：

```text
OWNER
ADMIN
MEMBER
```

---

# 6. Restaurant 数据模型

## 6.1 restaurants

```text
restaurants
--------------------------------
id                  BIGINT PK
name                VARCHAR
brand               VARCHAR NULL
category            VARCHAR
address             VARCHAR
longitude           DECIMAL
latitude            DECIMAL
location            GEOMETRY(Point)
phone               VARCHAR NULL
avg_price           DECIMAL NULL
cover_url           VARCHAR NULL
business_hours      JSONB NULL
source              VARCHAR
source_id           VARCHAR
status              SMALLINT
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

`location` 使用 PostGIS。

---

# 7. 群组餐厅模型

## 7.1 group_restaurants

```text
group_restaurants
--------------------------------
id                  BIGINT PK
group_id            BIGINT
restaurant_id       BIGINT

visit_count         INT
last_visit_at       TIMESTAMP NULL

group_score         DECIMAL
taste_score         DECIMAL
value_score         DECIMAL
environment_score   DECIMAL
service_score       DECIMAL
traffic_score       DECIMAL

created_at          TIMESTAMP
updated_at          TIMESTAMP

UNIQUE(group_id, restaurant_id)
```

这个表非常重要。

它表示：

> **某个群对某个餐厅的总体认知。**

---

# 8. 组队模型

建议将一次组队统一命名为：

```text
GroupEvent
```

## 8.1 group_events

```text
group_events
--------------------------------
id                  BIGINT PK
group_id            BIGINT

creator_id          BIGINT

restaurant_id       BIGINT NULL

title               VARCHAR

event_time          TIMESTAMP

min_members         INT
max_members         INT

latitude            DECIMAL NULL
longitude           DECIMAL NULL

remark              TEXT NULL

status              VARCHAR

created_at          TIMESTAMP
updated_at          TIMESTAMP
completed_at        TIMESTAMP NULL
```

状态：

```text
RECRUITING
CONFIRMED
COMPLETED
CANCELLED
```

---

# 9. 组队成员

## 9.1 event_members

```text
event_members
--------------------------------
id                  BIGINT PK
event_id            BIGINT
user_id             BIGINT

status              VARCHAR

joined_at            TIMESTAMP
updated_at           TIMESTAMP

UNIQUE(event_id, user_id)
```

状态：

```text
JOINED
LEFT
```

---

# 10. 评价模型

## 10.1 reviews

```text
reviews
--------------------------------
id                  BIGINT PK

restaurant_id       BIGINT
group_id            BIGINT
event_id            BIGINT
user_id             BIGINT

overall_score       DECIMAL
taste_score         DECIMAL
value_score         DECIMAL
environment_score   DECIMAL
service_score       DECIMAL
traffic_score       DECIMAL

content             TEXT

created_at          TIMESTAMP
updated_at          TIMESTAMP
```

这里明确建立：

```text
User
 ↓
Review
 ↓
Event
 ↓
Group
 ↓
Restaurant
```

因此可以回答：

> 张三对这家店怎么看？

也可以回答：

> 产品部这个群怎么看这家店？

还可以回答：

> 上次聚餐对这家店评价怎么样？

---

# 11. 组队与评价关系

一次完整聚餐：

```text
Group
 ↓
GroupEvent
 ↓
EventMember
 ↓
Restaurant
 ↓
Review
```

例如：

```text
产品部群
    │
    └── 2026-08-20 周五聚餐
            │
            ├── 张三
            ├── 李四
            ├── 王五
            │
            └── XX火锅
                    │
                    ├── 张三评价
                    ├── 李四评价
                    └── 王五评价
```

---

# 12. 评价聚合机制

用户评价提交以后：

```text
Review
 ↓
GroupRestaurant
 ↓
重新计算聚合评分
```

例如：

```text
group_restaurants

group_score = AVG(overall_score)

taste_score = AVG(taste_score)

value_score = AVG(value_score)

environment_score = AVG(environment_score)

service_score = AVG(service_score)

traffic_score = AVG(traffic_score)
```

MVP 可以使用简单平均。

以后再增加：

```text
时间衰减
评价可信度
参与次数权重
用户权重
```

---

# 13. API 设计

建议 REST API。

基础：

```text
/api/v1
```

---

# 14. 用户 API

### 登录

```http
POST /auth/wechat/login
```

请求：

```json
{
  "code": "wx-login-code"
}
```

返回：

```json
{
  "access_token": "...",
  "user": {
    "id": 10001,
    "nickname": "张三",
    "avatar_url": "..."
  }
}
```

---

# 15. 群组 API

### 创建群组

```http
POST /groups
```

### 群组列表

```http
GET /groups
```

### 群组详情

```http
GET /groups/{group_id}
```

### 加入群组

```http
POST /groups/{group_id}/join
```

### 邀请码加入

```http
POST /groups/join-by-code
```

### 成员列表

```http
GET /groups/{group_id}/members
```

### 退出群组

```http
POST /groups/{group_id}/leave
```

---

# 16. 组队 API

### 创建组队

```http
POST /groups/{group_id}/events
```

请求：

```json
{
  "title": "周五火锅",
  "restaurant_id": 10001,
  "event_time": "2026-08-21T18:30:00+08:00",
  "min_members": 2,
  "max_members": 6,
  "remark": "想吃火锅"
}
```

如果没有确定餐厅：

```json
{
  "title": "周五聚餐",
  "restaurant_id": null,
  "event_time": "2026-08-21T18:30:00+08:00",
  "min_members": 4,
  "max_members": 8
}
```

---

# 17. 地图组队 API

这是 MVP 的关键接口。

```http
GET /groups/{group_id}/events/map
```

参数：

```text
longitude
latitude
radius
status
start_time
end_time
```

返回：

```json
{
  "events": [
    {
      "id": 10001,
      "title": "周五火锅",
      "restaurant": {
        "id": 20001,
        "name": "XX火锅",
        "longitude": 116.123,
        "latitude": 39.123
      },
      "event_time": "2026-08-21T18:30:00+08:00",
      "current_members": 3,
      "max_members": 6,
      "status": "RECRUITING"
    }
  ]
}
```

前端直接转换为 Marker。

---

# 18. 加入组队

```http
POST /events/{event_id}/join
```

退出：

```http
POST /events/{event_id}/leave
```

查询：

```http
GET /events/{event_id}
```

成员：

```http
GET /events/{event_id}/members
```

完成：

```http
POST /events/{event_id}/complete
```

---

# 19. 店铺 API

### 搜索店铺

```http
GET /restaurants/search
```

参数：

```text
keyword
longitude
latitude
radius
category
```

MVP 可以首先直接调用高德 POI。

后端不要让小程序直接调用第三方地图 API。

应该：

```text
小程序
 ↓
Backend
 ↓
Amap
```

这样未来更换地图供应商不会影响前端。

---

# 20. 群组店铺 API

### 群组店铺

```http
GET /groups/{group_id}/restaurants
```

### 店铺详情

```http
GET /groups/{group_id}/restaurants/{restaurant_id}
```

返回：

```json
{
  "restaurant": {},
  "group_stats": {
    "visit_count": 5,
    "score": 4.7,
    "taste": 4.8,
    "value": 4.3,
    "environment": 4.7,
    "service": 4.5,
    "traffic": 4.2
  }
}
```

---

# 21. 评价 API

提交：

```http
POST /events/{event_id}/reviews
```

请求：

```json
{
  "overall_score": 5,
  "taste_score": 5,
  "value_score": 4,
  "environment_score": 5,
  "service_score": 4,
  "traffic_score": 4,
  "content": "味道不错，适合多人聚餐"
}
```

评价列表：

```http
GET /restaurants/{restaurant_id}/reviews
```

群组评价：

```http
GET /groups/{group_id}/restaurants/{restaurant_id}/reviews
```

---

# 22. 前端页面结构

建议：

```text
pages/
│
├── index/
│   └── index
│
├── group/
│   ├── list
│   ├── create
│   ├── detail
│   ├── members
│   └── join
│
├── event/
│   ├── create
│   ├── detail
│   ├── members
│   └── review
│
├── restaurant/
│   ├── search
│   ├── detail
│   └── reviews
│
└── user/
    └── profile
```

---

# 23. 首页交互流程

```text
打开小程序
 ↓
判断是否登录
 ↓
没有群组？
 ↓
创建 / 加入群组
 ↓
选择当前群组
 ↓
进入地图
 ↓
显示当前群组组队
```

如果用户有多个群：

```text
当前群组：

🔥 产品部
👨‍💻 程序员朋友
🏠 大学同学
```

用户切换群组：

```text
切换群组
 ↓
地图数据重新加载
 ↓
只显示该群组组队
```

---

# 24. 地图页面

核心组件：

```text
MapContainer
├── Map
├── GroupSelector
├── EventMarker
├── FilterBar
└── EventBottomSheet
```

用户点击 Marker：

```text
Marker
 ↓
BottomSheet
 ↓
组队信息
 ↓
[查看详情]
[加入组队]
```

---

# 25. 组队详情页

组件：

```text
EventDetail
├── EventHeader
├── RestaurantCard
├── MemberList
├── EventStatus
├── EventRemark
└── ActionBar
```

底部：

```text
[加入组队]
```

如果已经加入：

```text
[已加入]
```

如果自己创建：

```text
[管理组队]
```

---

# 26. 群组店铺详情

页面应该重点体现：

> **“我们群的人怎么看这家店？”**

例如：

```text
XX火锅

⭐⭐⭐⭐⭐ 4.7

我们群去过 8 次

口味     █████ 4.8
性价比   ████░ 4.3
环境     █████ 4.7
服务     ████░ 4.5
交通     ████░ 4.2

────────────────

群成员评价

张三：
“适合多人聚餐”

李四：
“价格稍微有点贵”

王五：
“味道不错”

────────────────

[发起组队]
```

---

# 27. 组队状态机

后端必须统一控制状态，不允许前端自行修改。

```text
CREATED
   ↓
RECRUITING
   │
   ├── CANCELLED
   │
   ↓
CONFIRMED
   │
   ↓
COMPLETED
   │
   ↓
REVIEWING
   │
   ↓
REVIEWED
```

MVP 可以实际只使用：

```text
RECRUITING
CONFIRMED
COMPLETED
CANCELLED
```

评价状态由是否存在评价判断，不必增加复杂状态。

---

# 28. 关键业务规则

### 组队人数

```text
current_members <= max_members
```

达到人数：

```text
current_members == max_members
```

自动：

```text
RECRUITING → CONFIRMED
```

---

### 重复加入

同一个用户不能重复加入：

```text
UNIQUE(event_id, user_id)
```

---

### 已结束组队

```text
COMPLETED
```

不能继续加入。

---

### 评价资格

只有：

```text
EventMember.status = JOINED
```

的用户才能评价。

---

### 一次聚餐只能评价一次

```text
UNIQUE(event_id, user_id)
```

---

# 29. 地图数据设计

地图不要一次返回整个城市所有组队。

采用：

```text
当前地图中心
+
地图视野范围
```

例如：

```text
GET /groups/{group_id}/events/map
```

根据：

```text
bbox
```

或者：

```text
center + radius
```

查询。

PostGIS：

```sql
ST_DWithin(
    location,
    user_location,
    radius
)
```

这样未来数据量扩大后也可以支撑。

---

# 30. 推荐的技术架构

```text
                 微信小程序
                      │
                      ↓
                 API Gateway
                      │
               FastAPI Backend
                      │
       ┌──────────────┼───────────────┐
       │              │               │
       ↓              ↓               ↓
    User Service   Group Service   Restaurant Service
       │              │               │
       │              ↓               ↓
       │           Event Service   POI Service
       │              │               │
       └──────────────┼───────────────┘
                      ↓
               Review Service
                      │
                      ↓
              Recommendation
              （MVP 暂时简单规则）
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
   PostgreSQL       Redis       Object Storage
   + PostGIS
        │
        ↓
    Restaurant Data
        │
        ↓
    高德地图 API
```

---

# 31. 技术栈

| 层级     | 技术                         |
| ------ | -------------------------- |
| 小程序    | 微信原生 / Taro                |
| 语言     | TypeScript                 |
| 后端     | Python                     |
| API    | FastAPI                    |
| ORM    | SQLAlchemy                 |
| 数据库    | PostgreSQL                 |
| GIS    | PostGIS                    |
| 缓存     | Redis                      |
| 异步任务   | Celery                     |
| 地图     | 高德地图                       |
| 文件     | OSS / COS                  |
| API 文档 | OpenAPI / Swagger          |
| 容器     | Docker                     |
| CI/CD  | GitHub Actions / GitLab CI |
| 日志     | Loki / ELK                 |
| 监控     | Prometheus + Grafana       |

如果你的团队更偏前端，也可以采用：

```text
Node.js
NestJS
PostgreSQL
PostGIS
Redis
```

整体架构不变。

---

# 32. 开发阶段规划

## Phase 0：项目初始化

目标：

```text
项目可以运行
前后端可以通信
数据库可以连接
```

任务：

* 创建 Git Repository
* 初始化小程序
* 初始化 FastAPI
* Docker Compose
* PostgreSQL
* Redis
* 环境变量
* API 规范
* CI
* 基础日志

---

# 33. Phase 1：用户与群组

开发：

```text
微信登录
 ↓
User
 ↓
创建 Group
 ↓
Join Group
 ↓
Group Member
```

完成：

* 登录
* 用户信息
* 创建群
* 邀请码
* 分享加入
* 群成员
* 群组切换

验收：

> 两个微信用户能够进入同一个群组，并看到彼此。

---

# 34. Phase 2：地图

开发：

```text
Map
 ↓
Location
 ↓
Amap
```

实现：

* 获取位置
* 地图显示
* POI 搜索
* 餐厅 Marker
* 店铺详情

验收：

> 用户可以在地图上找到餐厅，并查看基本信息。

---

# 35. Phase 3：组队

这是第一个核心里程碑。

开发：

* 创建组队
* 指定餐厅
* 不指定餐厅
* 时间
* 人数
* 备注
* 加入
* 退出
* 状态
* 地图 Marker
* 组队详情

验收：

```text
用户 A
 ↓
创建组队

用户 B
 ↓
地图看到

用户 C
 ↓
点击 Marker

用户 C
 ↓
加入

A/B/C
 ↓
看到相同成员状态
```

---

# 36. Phase 4：微信分享

实现：

```text
分享群组
分享组队
```

重点验证：

```text
用户 A 创建组队
 ↓
分享
 ↓
用户 B 点击
 ↓
打开小程序
 ↓
查看组队
 ↓
加入
```

这是 MVP 必须重点测试的场景。

---

# 37. Phase 5：群组餐厅库

实现：

```text
历史组队
 ↓
餐厅
 ↓
自动进入群组餐厅库
```

例如：

第一次：

```text
XX火锅
组队 1
```

第二次：

```text
XX火锅
组队 2
```

系统：

```text
XX火锅

我们群去过 2 次
```

---

# 38. Phase 6：评价系统

实现：

```text
完成组队
 ↓
评价提醒
 ↓
提交评价
 ↓
更新 GroupRestaurant
 ↓
展示群组评分
```

验收：

```text
4 个成员
 ↓
4 个评价
 ↓
系统自动计算
 ↓
群组评分
```

---

# 39. Phase 7：MVP 联调

完整走：

```text
微信登录
 ↓
创建群
 ↓
邀请
 ↓
地图
 ↓
找餐厅
 ↓
创建组队
 ↓
分享
 ↓
加入
 ↓
完成聚餐
 ↓
评价
 ↓
群组店铺库
 ↓
再次组队
```

如果这个闭环跑通：

> **MVP 就基本成立。**

---

# 40. 测试重点

## 核心业务测试

必须测试：

```text
多人同时加入
多人同时退出
达到人数上限
重复加入
组队取消
组队完成
重复评价
非参与成员评价
群组切换
分享链接
```

尤其需要测试：

### 并发加入

假设：

```text
最大人数 = 6

当前 = 5
```

两个用户同时点击：

```text
User A → Join
User B → Join
```

不能变成：

```text
7 / 6
```

后端需要事务 / 行锁保证。

---

# 41. MVP 账单功能决策

最终确定：

### MVP

只保留数据库扩展空间：

```text
group_events
    ↓
total_amount NULL
```

甚至第一版可以不建立。

### V1

增加：

```text
消费金额记录
人均金额
```

### V2

增加：

```text
AA
按人分摊
代付
账单
```

### V3

再考虑：

```text
支付
收款
退款
团购
```

这样不会污染 MVP 核心开发。

---

# 42. 推荐开发顺序

我建议实际编码严格按照：

```text
01 项目基础设施
        ↓
02 用户系统
        ↓
03 群组系统
        ↓
04 地图系统
        ↓
05 餐厅系统
        ↓
06 组队系统
        ↓
07 微信分享
        ↓
08 群组餐厅库
        ↓
09 评价系统
        ↓
10 MVP 联调
        ↓
11 测试
        ↓
12 灰度上线
```

不要先开发：

```text
AI
推荐算法
第三方点评
团购
分账
```

---

# 43. 第一版的核心指标

MVP 不要一开始追求 DAU。

真正应该观察：

### 组队转化率

```text
创建组队
 ↓
最终成功聚餐
```

### 加入率

```text
分享组队
 ↓
点击
 ↓
加入
```

### 评价率

```text
完成聚餐
 ↓
提交评价
```

### 复用率

```text
群组第一次聚餐
 ↓
第二次聚餐
```

尤其关注：

> **一个群组是否会在第一次聚餐之后继续使用。**

如果一个群组持续产生：

```text
组队 → 聚餐 → 评价 → 再组队
```

说明产品的核心价值成立。

---

# 44. MVP 最终架构总结

```text
                         微信小程序
                              │
        ┌─────────────────────┼────────────────────┐
        ↓                     ↓                    ↓
      地图                   群组                 我的
        │                     │
        ↓                     ↓
   组队 Marker           群组主页
        │                     │
        └──────────┬──────────┘
                   ↓
                 组队
                   │
        ┌──────────┼──────────┐
        ↓          ↓          ↓
      时间       人数       餐厅
                              │
                              ↓
                        聚餐完成
                              │
                              ↓
                           评价
                              │
                              ↓
                     GroupRestaurant
                              │
                              ↓
                       群组餐厅知识库
                              │
                              └──────→ 下一次组队
```

**第一阶段最重要的不是“餐厅数据多”，而是把这条闭环跑通。**

尤其建议你把 **`Group + GroupEvent + Restaurant + Review`** 作为第一版的四个核心领域模型。后续无论接入美团/点评数据、加入 AI 推荐、做智能筛选，甚至加入账单分摊，都可以在这个模型上自然扩展，而不需要推翻 MVP 架构。
