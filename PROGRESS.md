# 聚豆项目 · 进度快照（2026-08-23 暂存）

> 下次会话从「恢复操作」一节开始，按序执行即可继续。

## 一、任务清单状态

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | SSH 通道（密钥 `~/.ssh/ali_judou` → root@39.106.193.182） | ✅ 完成 | 免密登录已验证 |
| 2 | 服务器初始化（Docker Engine 29 + Compose v5.5，阿里云镜像源） | ✅ 完成 | 镜像加速：`docker.xuanyuan.me` 优先 |
| 3 | 聚豆栈部署到 `/opt/judouproject` | ✅ 完成 | health ok / PostGIS 3.4 / 微信真实登录通道验证通过 / 容器 `unless-stopped` 自愈 / 高德真实 POI 验证通过（杭州 20 条真实数据） |
| 4 | **用户提交 ICP 备案** | ⏸️ 等待用户 | beian.aliyun.com，操作清单见下 |
| 5 | 备案通过后：Nginx 反代 + Let's Encrypt + DNS 解析 | ⏳ 阻塞于 #4 | 80/443 安全组放行也在这步做 |
| 6 | 小程序后台加合法域名 + 更新 config.ts | ⏳ 阻塞于 #4 | |
| 7 | 全链路验证（体验版真机免调试模式） | ⏳ 阻塞于 #4 | |
| 8 | 地图 mock 数据诊断（根因：AMAP_KEY 为空） | ✅ 完成 | |
| 9 | 高德 Key 写入本机+服务器 .env 并验证 | ✅ 完成 | ⚠️ 改 .env 后必须 `up -d --force-recreate`（docker restart 不刷新 env_file） |
| 10 | 朋友扫码"暂无体验权限"（根因：预览码只有开发者本人能扫） | ✅ 完成 | 已给出体验版 4 步流程，用户执行中 |
| 11 | 进度快照写入工作区 | 本文件 | |

## 二、环境拓扑（两套并行）

### A. 阿里云服务器（正式部署，待备案激活）
- 主机：`root@39.106.193.182`（Ubuntu 22.04，2C2G40G，SWAS 轻量）
- 代码：`/opt/judouproject`（master）；`.env` 已含：随机 JWT_SECRET、微信 AppID/Secret、高德 Key
- 容器：judou-backend / judou-postgres / judou-redis（restart=unless-stopped，docker 开机自启）
- 当前仅 8000 端口本机可访问；80/443 未开放（备案后再配 Nginx/HTTPS）
- **数据库全新空库**（用户选择不迁移本机测试数据）
- 检查命令：`ssh -i ~/.ssh/ali_judou root@39.106.193.182 'docker ps && curl -s http://127.0.0.1:8000/api/v1/health'`

### B. 本机（过渡期给朋友内测用）
- Docker Desktop（Windows）：容器 judou-backend / judou-postgres / judou-redis / judou-tunnel，网络 `deploy_default`
- 后端：`deploy/docker-compose.yml` 起的容器（或 venv 直跑）；`.env` 已含微信/高德凭据（与服务器独立值）
- 隧道：`judou-tunnel` = cloudflared trycloudflare（**免费共享，随时会被回收**），必须带 `--protocol http2`（本机 QUIC/UDP 被干扰，QUIC 连不上边缘）
- 小程序入口：`miniprogram/utils/config.ts` 的 BASE_URL = 当前隧道 URL + `/api/v1`
- 朋友访问方式：体验版二维码（开发者已把朋友加为体验成员）+ 真机开一次调试模式（trycloudflare 未备案，必须跳过域名校验）

## 三、已知坑（别再踩）

1. **trycloudflare 隧道不稳定**：过夜/断线会死（已多次）。恢复：`powershell -ExecutionPolicy Bypass -File deploy/restart-tunnel.ps1`（会自动改 config.ts）→ **重新生成体验版**（开发者工具「上传」+ 后台「选为体验版」）→ 朋友重新扫码。或直接删旧码重发。
2. **预览码 ≠ 体验版**：预览码只有开发者本人微信能扫；朋友必须走体验版（后台加体验成员 + 上传 + 选为体验版）。
3. **改 .env 必须 `up -d --force-recreate`**，`docker restart` 不重新加载 env_file。
4. **GitHub 认证**：Windows 凭据管理器的 token 曾失效；用户已处理过一次，push 失败时让用户在终端推一次刷新凭据。
5. **国内网络**：GitHub 直连下载会被 reset（用 winget/镜像）；Docker Hub 直连超时（服务器已配 `docker.xuanyuan.me` 加速）；get.docker.com 被墙（用阿里云 apt 源装 Docker）。
6. **微信登录已是真实模式**（两侧均配置 AppID/Secret）：fake code 会 500（微信 40029），属预期；测试拿 token 用 `docker exec judou-backend python -c "from app.core.security import create_access_token; print(create_access_token(用户ID))"`。
7. 高德个人版配额 5000 次/日，内测够用。

## 四、下次会话恢复操作

```bash
# 1. 检查服务器（应全绿）
ssh -i ~/.ssh/ali_judou root@39.106.193.182 'docker ps --format "{{.Names}} {{.Status}}"; curl -s http://127.0.0.1:8000/api/v1/health'

# 2. 检查/恢复本机栈（Docker Desktop 若没运行先启动它，等 20-30s）
cd /d/Code/Python_Workspace/JuDouProject
docker compose -f deploy/docker-compose.yml up -d postgres redis backend
curl -s http://localhost:8000/api/v1/health

# 3. 隧道大概率已死，重建（--protocol http2 不能漏）
docker rm -f judou-tunnel
docker run -d --name judou-tunnel --network deploy_default cloudflare/cloudflared tunnel --url http://backend:8000 --no-autoupdate --protocol http2
sleep 18 && docker logs judou-tunnel | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1
# 4. 若新 URL 与 config.ts 不一致：用 deploy/restart-tunnel.ps1 或手动改 miniprogram/utils/config.ts
```

## 五、用户侧待办（阻塞主线）

1. **提交 ICP 备案**（最优先，1-3 周审核）：
   - 阿里云控制台确认域名**实名认证**通过（未实名不能备案）
   - SWAS 控制台 →「ICP备案」→ 获取备案服务号
   - beian.aliyun.com 提交个人备案（网站名避免"官网/公司/商城/平台"字眼；保持手机畅通，通管局可能电话核实）
2. 备案期间朋友内测：体验版二维码 + 真机调试模式（如隧道断按上面第 3 步恢复）

## 六、工作区未提交改动（暂存时状态）

```
M  miniprogram/utils/config.ts        # BASE_URL 指向当时的隧道
?? deploy/restart-tunnel.ps1          # 隧道应急脚本
M  .idea/*.xml、project.config.json   # IDE 本地配置（未提交）
```
`deploy/.env` 已被 .gitignore 忽略（含凭据，勿提交）。

## 七、凭据位置（只记位置，值不回显）

- 微信 AppID/Secret：本机 `deploy/.env` + 服务器 `/opt/judouproject/deploy/.env`
- 高德 Web服务 Key：同上两处
- JWT_SECRET：本机/服务器各自独立随机值，同上
- SSH 私钥：本机 `~/.ssh/ali_judou`

## 八、备案通过后的交接（#5-#7）

1. 用户：安全组放行 80/443；阿里云 DNS 加 A 记录 `api.judou域名 → 39.106.193.182`
2. 我：服务器装 Nginx 反代 8000 + certbot 签 HTTPS（备案下来域名可解析即可签）
3. 我：config.ts 切 `https://api.域名/api/v1`，重新上传选体验版
4. 用户：小程序后台「request 合法域名」加 `https://api.域名`
5. 验证：体验版真机**不开**调试模式可登录 → 全链路完成，隧道/预览码方案退役
