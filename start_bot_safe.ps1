# AI Trading Bot Starter - Windows Console Safe Version
# Fixes emoji encoding issues on Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AI TRADING BOT - STARTING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set UTF-8 encoding for PowerShell console
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Set PYTHONPATH
$env:PYTHONPATH = "."

# Start Docker containers
Write-Host "[1/3] Starting Prometheus & Grafana..." -ForegroundColor Yellow
Set-Location monitoring
docker-compose up -d 2>&1 | Out-Null
Set-Location ..
Write-Host "      Prometheus: http://localhost:9090" -ForegroundColor Green
Write-Host "      Grafana:    http://localhost:3000 (admin/admin)" -ForegroundColor Green
Write-Host ""

# Wait for containers to start
Write-Host "[2/3] Waiting for containers to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Write-Host "      Done!" -ForegroundColor Green
Write-Host ""

# Start bot
Write-Host "[3/3] Starting AI Trading Bot..." -ForegroundColor Yellow
Write-Host "      Bot Metrics: http://localhost:8000/metrics" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the bot" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set PYTHONUNBUFFERED for live output
$env:PYTHONUNBUFFERED = "1"

python -u -m infrastructure.scheduler_runner

