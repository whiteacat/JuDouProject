// 全局配置
// 开发模式（开发者工具/真机调试）：可用 http://localhost:8000 或电脑局域网 IP，勾选「不校验合法域名」
// 公网临时隧道（cloudflared trycloudflare）：每次重启隧道 URL 都会变，需同步更新此文件与小程序后台 request 合法域名
// 生产环境：改为已备案的 HTTPS 域名，并在小程序后台配置 request 合法域名
export const BASE_URL = 'https://far-negotiations-cleveland-ata.trycloudflare.com/api/v1'
