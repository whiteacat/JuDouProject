# 隧道应急重启脚本：trycloudflare URL 失效/电脑重启后，一条命令恢复外网访问。
#
# 用法（PowerShell）：
#   powershell -ExecutionPolicy Bypass -File deploy/restart-tunnel.ps1
#
# 作用：
#   1. 重启 judou-tunnel 容器（与 backend 同一 docker 网络，走 backend:8000 服务名）
#   2. 从容器日志提取新的 trycloudflare URL
#   3. 自动更新 miniprogram/utils/config.ts 的 BASE_URL
#
# 之后你还需要手动做两步（脚本无法代劳）：
#   - 小程序开发者工具重新上传代码（体验版需再分发）
#   - 小程序后台「request 合法域名」替换为新 URL（如需体验版/正式版长期访问）
#
# 前置：Docker Desktop 已启动（postgres/redis/backend 容器在运行）。

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot          # 仓库根目录
$ConfigTs = Join-Path $Root "miniprogram/utils/config.ts"

# --- 0. 前置检查 ---
try { docker info *> $null } catch {
    Write-Host "[ERROR] Docker 未运行，请先启动 Docker Desktop 后再试。" -ForegroundColor Red
    exit 1
}

# backend 容器健康检查（隧道目标必须可达，否则朋友拿到的是 502）
if (-not (docker ps --format "{{.Names}}" | Select-String -SimpleMatch "judou-backend")) {
    Write-Host "[WARN] judou-backend 容器未运行，先启动 backend：" -ForegroundColor Yellow
    Write-Host "  docker compose -f deploy/docker-compose.yml up -d backend" -ForegroundColor Yellow
    exit 1
}

# --- 1. 重建隧道容器 ---
Write-Host "==> 停止并删除旧隧道容器 judou-tunnel ..."
docker rm -f judou-tunnel 2>&1 | Out-Null

# 网络名随 compose 项目名变化（默认 deploy_default），自动探测
$Network = docker network ls --format "{{.Name}}" |
    Where-Object { $_ -match "^(deploy|judou)_default$" } | Select-Object -First 1
if (-not $Network) {
    Write-Host "[ERROR] 未找到 compose 网络（deploy_default / judou_default）。" -ForegroundColor Red
    exit 1
}

Write-Host "==> 启动新隧道（网络: $Network，目标 backend:8000）..."
docker run -d --name judou-tunnel --network $Network `
    cloudflare/cloudflared tunnel --url http://backend:8000 --no-autoupdate | Out-Null

# --- 2. 等待并提取 URL ---
$Url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    $Url = docker logs judou-tunnel 2>&1 |
        Select-String -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" |
        Select-Object -First 1
    if ($Url) { $Url = $Url.Matches[0].Value; break }
}
if (-not $Url) {
    Write-Host "[ERROR] 30 秒内未从隧道日志提取到 URL，请手动检查：docker logs judou-tunnel" -ForegroundColor Red
    exit 1
}
$Url = $Url.Trim()
Write-Host "==> 新隧道 URL: $Url" -ForegroundColor Green

# --- 3. 外网自检（health 必须 200 才算恢复） ---
$Health = try {
    (Invoke-WebRequest -Uri "$Url/api/v1/health" -TimeoutSec 15 -UseBasicParsing).StatusCode
} catch { $null }
if ($Health -ne 200) {
    Write-Host "[WARN] 隧道 health 自检未通过（$Health），Cloudflare 侧可能还在生效，几秒后通常自动恢复。" -ForegroundColor Yellow
} else {
    Write-Host "==> 外网 health 自检通过 (200)" -ForegroundColor Green
}

# --- 4. 更新 config.ts ---
$Content = Get-Content $ConfigTs -Raw -Encoding UTF8
if ($Content -match "https://[a-z0-9-]+\.trycloudflare\.com") {
    $NewContent = [regex]::Replace($Content, "https://[a-z0-9-]+\.trycloudflare\.com", $Url)
    [System.IO.File]::WriteAllText($ConfigTs, $NewContent, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "==> config.ts 的 BASE_URL 已更新为新 URL" -ForegroundColor Green
} else {
    Write-Host "[WARN] config.ts 中未找到 trycloudflare URL，请手动确认 BASE_URL。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "完成。剩余手动步骤：" -ForegroundColor Cyan
Write-Host "  1. 微信开发者工具重新编译 + 上传代码"
Write-Host "  2. 小程序后台「request 合法域名」替换为新 URL（体验版/正式版需要）"
