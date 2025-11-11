# ========================================
# Scheduler Başlatma Scripti
# ========================================

# Proje kök dizinine git
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# UTF-8 Encoding Ayarları (Windows için gerekli)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Console encoding ayarla
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "🚀 Starting Scheduler..." -ForegroundColor Green
Write-Host "📁 Project Root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "🔧 PYTHONIOENCODING: $env:PYTHONIOENCODING" -ForegroundColor Cyan
Write-Host ""

# PYTHONPATH'e GEREK YOK! Python modülü olarak çalıştırıyoruz
python -m infrastructure.scheduler_runner

