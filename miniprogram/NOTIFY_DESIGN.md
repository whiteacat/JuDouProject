# JuDou 通知系统设计

> 日期：2026-09-14
> 范围：站内通知中心（一期）+ 微信订阅消息（二期，依赖模板配置）
> 设计原则：服务端事件驱动、只推「与我相关」的通知、模板化文案、可配置开关

---

## 一、总体架构

```
业务写入点（event_service / review_service / group_service）
        │  状态变更成功后调用
        ▼
notification_service.notify(user_id, type, payload)
        │  1. 站内：写 notifications 表（模板渲染文案）
        │  2. 微信（二期）：调订阅消息 API（用户已授权时）
        ▼
notifications 表（每用户通知流，已读/未读）
        │
        ├── GET /notifications（列表 + 未读数）
        ├── POST /notifications/{id}/read（单条已读）
        ├── POST /notifications/read-all（全部已读）
        └── 未读数角标：tabbar 个人中心 + 通知页标题
```

**为什么站内通知优先：** 微信订阅消息需要用户在每次操作时主动授权（一次性订阅），无法做到"必达"；站内通知不依赖外部配置、实现成本低、可离线补齐，是可靠基座。微信订阅消息作为二期增强（用户主动订阅后才推），两者共用同一套 `notify` 入口，互不阻塞。

---

## 二、通知场景模板（核心）

共 **9 类场景**，分 3 组。每类模板含：触发条件、接收人、文案模板（占位符）、跳转目标。

### A. 活动状态类（最重要，6 类）

| # | 类型标识 | 触发条件（写入点） | 接收人 | 文案模板 | 跳转 |
|---|---|---|---|---|---|
| 1 | `event_confirmed` | `confirm_event` 满员确认后 | 除确认人外的所有已加入成员 | 「{event_title}」已确认：{time_text} 在 {restaurant_name} 集合，请准时参加 | 活动详情 |
| 2 | `event_cancelled` | `cancel_event` | 该活动全部已加入成员 | 「{event_title}」已被{actor_nickname}取消，原因是：{reason} | 活动详情 |
| 3 | `event_completed` | `complete_event` | 全部参与成员 | 「{event_title}」已完成，感谢参与！去写评价分享你的聚餐体验吧 | 活动详情 |
| 4 | `member_joined` | `join_event` 成功 | 活动创建者（+已加入成员，可配置，默认仅创建者避免打扰） | {nickname} 加入了你的活动「{event_title}」，当前 {current}/{max} 人 | 活动详情 |
| 5 | `member_left` | `leave_event` 成功 | 活动创建者 | {nickname} 退出了活动「{event_title}」，当前 {current}/{max} 人 | 活动详情 |
| 6 | `event_reminder`（二期） | 定时任务：活动前 24h 触发 | 全部已加入成员 | 明天 {time_text} 「{event_title}」在 {restaurant_name} 集合，别迟到 | 活动详情 |

### B. 互动类（2 类）

| # | 类型标识 | 触发条件（写入点） | 接收人 | 文案模板 | 跳转 |
|---|---|---|---|---|---|
| 7 | `new_review` | `submit_review` 成功后 | 活动创建者 + 其他参与成员（排除自己） | {nickname} 给「{event_title}」留下了 {score} 星评价：「{review_snippet}」 | 活动详情 |
| 8 | `group_created_invite`（二期） | `create_group` 成功后 | 邀请的初始成员 | {nickname} 创建了群组「{group_name}」，邀请你一起聚餐 | 群组详情 |

### C. 系统类（1 类）

| # | 类型标识 | 触发条件 | 接收人 | 文案模板 | 跳转 |
|---|---|---|---|---|---|
| 9 | `system` | 管理员手动 / 内容开关变更 | 全体 / 部分用户 | {content}（如"平台内容编辑功能已暂停"） | 无 |

### 占位符约定

- 所有占位符由服务端渲染，前端只展示成品文案（安全：用户昵称/标题不做前端拼接，避免 XSS 类注入展示）
- `review_snippet` 截断 30 字 + 省略号；`time_text` 格式「周X HH:mm」
- 文案模板集中在 `notification_service.TEMPLATES` 字典，运营改文案不发版（存 app_settings，见第四节）

---

## 三、数据模型

### notifications 表（迁移 `b8c9d0e1f2a3`）

```sql
CREATE TABLE notifications (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL,          -- 接收人
    type          VARCHAR(32) NOT NULL,     -- 上表类型标识
    title         VARCHAR(64) NOT NULL,     -- 短标题（列表页小标题，如"活动已确认"）
    content       TEXT NOT NULL,            -- 渲染后的完整文案
    target_type   VARCHAR(16),              -- event / group / none
    target_id     BIGINT,                   -- 跳转目标 ID
    actor_id      BIGINT,                   -- 触发动作的用户（"谁"）
    actor_name    VARCHAR(64),              -- 触发人昵称（冗余，避免联查）
    is_read       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
```

设计要点：
- `actor_name` 冗余存储（用户改昵称后历史通知文案不漂移）
- 只建 `(user_id, is_read, created_at)` 复合索引：覆盖"我的通知列表 + 未读数"两个高频查询
- 不做软删除；`DELETE` 仅用于单条删除（可选功能）

### 前端页面结构

```
pages/user/notifications/     ← 新增：通知列表页
├── index.ts                   # 列表加载、单条已读、全部已读、空态
├── index.wxml                 # 通知卡片（图标按 type 分类 + 标题 + 文案 + 时间）
└── index.wxss
入口（3 处）：
├── 个人中心「我的通知」行（未读数角标）
├── tabbar 个人中心页右上角小铃铛（未读数角标，wx:if 控制）
└── 活动详情页：被取消/确认时顶部 toast 提示 + 引导看通知中心
```

未读数获取：`GET /notifications?unread_only=1` 的 `total` 字段（或专用 `GET /notifications/unread-count`，推荐后者，轻量）。

---

## 四、API 设计

| 方法 | 路径 | 说明 | 响应 |
|---|---|---|---|
| GET | `/notifications` | 我的通知列表，`page`/`size` 分页，按时间倒序 | `{ items: NotificationOut[], total }` |
| GET | `/notifications/unread-count` | 未读数（角标用） | `{ count }` |
| POST | `/notifications/{id}/read` | 单条标记已读（幂等） | `204` |
| POST | `/notifications/read-all` | 全部标记已读 | `204` |
| DELETE | `/notifications/{id}` | 删除单条（可选，一期先不做） | `204` |

`NotificationOut`：`id, type, title, content, target_type, target_id, actor_name, is_read, created_at`

### 配置开关（app_settings 表扩展，迁移并入 b8c9d0e1f2a3）

| key | 默认 | 说明 |
|---|---|---|
| `notify_enabled` | true | 站内通知总开关（false 时 notify 静默跳过，业务不受影响） |
| `notify_member_join` | true | 成员加入/退出通知（默认仅创建者收） |
| `notify_review` | true | 新评价通知 |

---

## 五、微信订阅消息（二期）

**前提：** 用户在触发点（加入活动/确认活动）时调用 `wx.requestSubscribeMessage` 一次性授权，后端存 `subscriptions(user_id, template_id, quota_left)`。

**需申请的模板（3 个）：**

| 模板场景 | 模板字段建议 | 对应站内类型 |
|---|---|---|
| 活动确认通知 | 活动名称 thing / 集合时间 time / 集合地点 thing / 备注 thing | event_confirmed |
| 活动取消通知 | 活动名称 thing / 取消时间 time / 取消原因 thing | event_cancelled |
| 活动提醒通知 | 活动名称 thing / 活动时间 time / 地点 thing | event_reminder |

**流程：**
```
用户点「加入组队」→ wx.requestSubscribeMessage([TMPL_CONFIRM, TMPL_CANCEL, TMPL_REMINDER])
    → POST /subscriptions/authorize { template_ids: [...] }
    → 后端 quota_left += 1（按模板分别计数）
活动状态变更 → notify() → 查用户该模板 quota_left > 0
    → 调 sendsubscribe 推送 → quota_left -= 1
```

**限制与降级：**
- 一次授权只推一条（每模板独立配额），用户不授权则只有站内通知
- 推送失败不重试（微信侧有 3 秒超时），仅记录日志
- 模板 ID 存 `app_settings`（`wx_template_confirm` 等），未配置时自动跳过微信推送

---

## 六、实施分期

### 一期（站内通知中心，纯本项目内闭环，约 1.5 天工作量）

1. 后端：
   - [ ] 迁移 `b8c9d0e1f2a3`：notifications 表 + app_settings 三个 notify 配置
   - [ ] `notification_service.py`：TEMPLATES 模板字典 + `notify()` 批量写入 + 配置开关检查
   - [ ] 写入点接入（6 处）：`confirm_event` / `cancel_event` / `complete_event` / `join_event` / `leave_event` / `submit_review`
   - [ ] `notifications.py` API：列表 / 未读数 / 单条已读 / 全部已读
   - [ ] 部署 + 端到端验证（建活动→加入→确认，查通知列表）
2. 小程序：
   - [ ] `pages/user/notifications/` 列表页（分页、点击跳转+已读、空态）
   - [ ] 个人中心「我的通知」入口 + 未读角标
   - [ ] 详情页返回时刷新未读数（onShow）

### 二期（微信订阅消息 + 提醒，依赖外部配置）

1. 微信公众平台申请 3 个模板，拿到模板 ID 配置到服务器
2. 后端：subscriptions 表 + authorize API + 推送服务（复用 notify 入口）
3. 小程序：加入/确认活动时 `wx.requestSubscribeMessage` 授权 + 授权上报
4. 定时任务：活动前 24h 提醒（APScheduler 或独立 cron 容器）

---

## 七、验收标准（一期）

- 用户 A 创建活动 → 用户 B 加入 → A 收到 `member_joined`（B 不收到自己触发的）
- A 确认活动 → B/C 收到 `event_confirmed`（A 不收到）
- A 取消活动 → 全体已加入成员收到 `event_cancelled`（含原因）
- 点击通知卡片 → 跳转对应活动详情 + 该条标记已读 + 角标 -1
- 通知开关 `notify_enabled=false` 后，业务操作正常、通知不再产生
- 通知列表空态展示「暂无通知」
