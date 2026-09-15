# 本地一键启动演示（无需 Docker）：本机 Redis + FastAPI(SQLite)
# 用法：  .\start-demo.ps1
# 启动后打开 http://localhost:8080

$ErrorActionPreference = "Stop"

# redis-server 路径（winget 安装的 redis-windows-fork；找不到时请改这里）
$redisExe = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\taizod1024.redis-windows-fork_Microsoft.Winget.Source_8wekyb3d8bbwe\Redis-8.10.1-Windows-x64-msys2\redis-server.exe"

if (-not (Get-Process redis-server -ErrorAction SilentlyContinue)) {
    Write-Host "启动 Redis (port 6379) ..."
    Start-Process -WindowStyle Hidden $redisExe -ArgumentList "--port", "6379"
    Start-Sleep -Seconds 2
}

$env:DATABASE_URL = "sqlite:///./demo.db"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:SYNC_TASK_ENABLED = "true"

Write-Host ""
Write-Host "ShortLink Demo 已启动 -> http://localhost:8080"
Write-Host "Swagger 文档       -> http://localhost:8080/docs"
Write-Host "端到端演示脚本     -> python scripts/demo_e2e.py"
Write-Host "Ctrl+C 停止服务"
Write-Host ""
.venv\Scripts\python -m uvicorn app.main:app --port 8080
