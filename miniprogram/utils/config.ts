// 全局配置
// 开发模式（开发者工具/真机调试）：可用 http://localhost:8000 或电脑局域网 IP，勾选「不校验合法域名」
// 公网临时隧道（cloudflared trycloudflare）：每次重启隧道 URL 都会变，需同步更新此文件与小程序后台 request 合法域名
// 本地开发：直连本机后端（Docker 容器 judou-backend，8000 端口）
// 开发者工具需勾选「详情 → 本地设置 → 不校验合法域名…」（http 且非 localhost 白名单域名）
// 生产环境：改为已备案的 HTTPS 域名，并在小程序后台配置 request 合法域名
export const BASE_URL = 'http://localhost:8000/api/v1'
