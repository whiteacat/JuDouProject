# 聚豆（JuDou）· 群组聚餐组队微信小程序

以群组为核心、地图为入口、组队为核心行为、群组餐厅评价库为长期数据资产的多人聚餐组队工具（MVP）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 小程序 | 微信原生 + TypeScript |
| 后端 | Python 3.9+ / FastAPI / SQLAlchemy 2.0 (async) / Alembic |
| 数据库 | PostgreSQL 16 + PostGIS |
| 缓存 | Redis |
| 地图 | 高德 POI（后端代理；未配置 key 时走 mock 数据） |
| 鉴权 | 微信 code2session → JWT（未配置 AppID 时走 mock 登录） |

## 快速开始

1. 环境：Docker Desktop（国内网络见 `deploy/.env.example` 与 Dockerfile 中 `PIP_INDEX_URL` 说明）
2. 配置：`cp deploy/.env.example deploy/.env`，按需填写 `AMAP_KEY`（高德 Web 服务 key）、`WECHAT_APPID`/`WECHAT_SECRET`（不填则 mock）
3. 启动：`docker compose -f deploy/docker-compose.yml up -d --build`
4. 验证：`curl http://localhost:8000/api/v1/health`；API 文档：http://localhost:8000/docs
5. 小程序：微信开发者工具导入 `miniprogram/`；本地开发勾选「详情 → 本地设置 → 不校验合法域名、web-view、TLS」

## 测试

```bash
cd backend && python -m pytest      # 依赖真实数据库（docker 起 postgres）
cd miniprogram && npx tsc --noEmit
```

## 上线准备清单

- [ ] 正式 AppID/Secret：填入 `deploy/.env`（未配置时后端自动走 mock 登录）
- [ ] HTTPS 合法域名：后端域名加入小程序后台「request 合法域名」；将 `miniprogram/utils/config.ts` 的 `BASE_URL` 改为线上地址
- [ ] 高德 Web 服务 key：`AMAP_KEY`（已支持；个人认证 5000 次/日）
- [ ] JWT 密钥：`JWT_SECRET` 改为强随机值（当前默认值仅限开发）
- [ ] 体验版灰度：开发者工具上传 → 体验版二维码 → 小范围验证核心闭环后再发布

## 里程碑

M0 基础设施 → M1 用户/微信登录 → M2 群组 → M3 地图/餐厅 → M4 组队（并发满员） → M5 微信分享 → M6 评价/群组餐厅库 → M7 MVP 联调闭环 → M8 测试加固/上线准备

详细设计见 `Architect&Plan.md`，开发计划见 `DEVELOPMENT_PLAN.md`。
