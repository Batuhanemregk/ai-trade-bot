# ========================================
# AI Trading Bot - Developer Scripts
# Quick commands for development workflow
# ========================================

# Set development environment
$env:APP_ENV = "dev"
$env:DEV_CONSOLE = "1"
$env:LOG_LEVEL = "DEBUG"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = "."
$env:CONSOLE_LOG = "1"
$env:LOG_EMOJI = "1"

# ========================================
# UTF-8 ENCODING SETUP
# ========================================

# Set UTF-8 environment variables
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LANG = "C.UTF-8"

# Configure PowerShell for UTF-8
try {
    # Set console code page to UTF-8 (silent)
    chcp 65001 | Out-Null
    # Set PowerShell output encoding to UTF-8
    $OutputEncoding = [System.Text.UTF8Encoding]::new()
    Write-Host "✅ UTF-8 encoding active (PowerShell)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ UTF-8 setup warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Check PowerShell version and recommend PS7
$PSVersion = $PSVersionTable.PSVersion
if ($PSVersion.Major -lt 7) {
    Write-Host "💡 Tip: PowerShell 7+ recommended for better UTF-8 support" -ForegroundColor Cyan
}

# Navigate to project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# ========================================
# PYTHON DETECTION
# ========================================

function Get-PythonPath {
    param(
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    # Eğer NoVenv belirtilmişse sistem Python kullan
    if ($NoVenv) {
        $pythonCandidates = @("py", "python", "python3")
        foreach ($cmd in $pythonCandidates) {
            if (Get-Command $cmd -ErrorAction SilentlyContinue) {
                return $cmd
            }
        }
        throw "Python bulunamadı! Lütfen Python 3.11+ yükleyin."
    }
    
    # Eğer VenvPath belirtilmişse
    if ($VenvPath) {
        $venvPython = Join-Path $VenvPath "Scripts\python.exe"
        if (Test-Path $venvPython) {
            return $venvPython
        }
        throw "Venv bulunamadı: $VenvPath"
    }
    
    # Varsayılan venv konumlarını kontrol et
    $venvLocations = @("venv\Scripts\python.exe", ".venv\Scripts\python.exe")
    foreach ($venv in $venvLocations) {
        if (Test-Path $venv) {
            return $venv
        }
    }
    
    # Venv bulunamadıysa sistem Python kullan
    Write-Host "⚠️  Venv bulunamadı, sistem Python kullanılıyor..." -ForegroundColor Yellow
    $pythonCandidates = @("py", "python", "python3")
    foreach ($cmd in $pythonCandidates) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            return $cmd
        }
    }
    
    throw "Python bulunamadı! Lütfen venv oluşturun veya Python 3.11+ yükleyin."
}

# ========================================
# FUNCTIONS
# ========================================

function Show-Banner {
    param([string]$Title, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $Color
    Write-Host " $Title" -ForegroundColor $Color
    Write-Host "========================================" -ForegroundColor $Color
    Write-Host ""
}

function Show-Python {
    param(
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "PYTHON CONFIGURATION" "Cyan"
    
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        Write-Host "Python executable: " -NoNewline -ForegroundColor Yellow
        Write-Host $pythonPath -ForegroundColor White
        
        $version = & $pythonPath --version 2>&1
        Write-Host "Version: " -NoNewline -ForegroundColor Yellow
        Write-Host $version -ForegroundColor White
        
        $location = & $pythonPath -c "import sys; print(sys.executable)" 2>&1
        Write-Host "Location: " -NoNewline -ForegroundColor Yellow
        Write-Host $location -ForegroundColor White
        
        Write-Host ""
    } catch {
        Write-Host "❌ Hata: $_" -ForegroundColor Red
    }
}

function Install-Req {
    param(
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "INSTALLING REQUIREMENTS" "Magenta"
    
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        Write-Host "Using Python: $pythonPath" -ForegroundColor Cyan
        Write-Host ""
        
        & $pythonPath -m pip install --upgrade pip
        & $pythonPath -m pip install -r requirements.txt
        
        Write-Host ""
        Write-Host "✅ Requirements installed successfully!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Hata: $_" -ForegroundColor Red
    }
}

function Start-Trading {
    param(
        [switch]$Once,
        [int]$Timeout = 0,
        [switch]$DryRun,
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "STARTING TRADING BOT (DEV MODE)" "Green"
    
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        
        $arguments = @("-u", "-m", "infrastructure.runtime", "trading")
        
        if ($Once) { $arguments += "--once" }
        if ($Timeout -gt 0) { $arguments += "--timeout", $Timeout }
        if ($DryRun) { $env:TRADING_MODE = "DRY_RUN" }
        
        Write-Host "Python: $pythonPath" -ForegroundColor Cyan
        Write-Host "Environment:" -ForegroundColor Yellow
        Write-Host "  APP_ENV       = $env:APP_ENV" -ForegroundColor White
        Write-Host "  LOG_LEVEL     = $env:LOG_LEVEL" -ForegroundColor White
        Write-Host "  DEV_CONSOLE   = $env:DEV_CONSOLE" -ForegroundColor White
        if ($env:TRADING_MODE) {
            Write-Host "  TRADING_MODE  = $env:TRADING_MODE" -ForegroundColor White
        } else {
            Write-Host "  TRADING_MODE  = PAPER" -ForegroundColor White
        }
        Write-Host ""
        
        & $pythonPath @arguments
    } catch {
        Write-Host "❌ Hata: $_" -ForegroundColor Red
    }
}

function Start-Telegram {
    param(
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "STARTING TELEGRAM BOT" "Cyan"
    
    # Load .env file if exists
    $envFile = Join-Path $ProjectRoot ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*([^#=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
        Write-Host "✅ Loaded .env file" -ForegroundColor Green
    }
    
    # Check if Telegram is enabled
    $telegramEnabled = if ($env:TELEGRAM_ENABLED) { $env:TELEGRAM_ENABLED.ToLower() -eq 'true' } else { $true }
    
    if (-not $telegramEnabled) {
        Write-Host "⚠️  Telegram bot is disabled (TELEGRAM_ENABLED=false)" -ForegroundColor Yellow
        return
    }
    
    # Check for token
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        Write-Host "❌ TELEGRAM_BOT_TOKEN not found in .env" -ForegroundColor Red
        Write-Host "   Please add TELEGRAM_BOT_TOKEN=your_token to .env file" -ForegroundColor Yellow
        return
    }
    
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        
        Write-Host "Python: $pythonPath" -ForegroundColor Cyan
        Write-Host "Environment:" -ForegroundColor Yellow
        Write-Host "  TELEGRAM_BOT_TOKEN = $($env:TELEGRAM_BOT_TOKEN.Substring(0, [Math]::Min(10, $env:TELEGRAM_BOT_TOKEN.Length)))..." -ForegroundColor White
        Write-Host "  TELEGRAM_CHAT_ID   = $($env:TELEGRAM_CHAT_ID)" -ForegroundColor White
        Write-Host ""
        Write-Host "✅ Starting Telegram bot..." -ForegroundColor Green
        Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
        Write-Host ""
        
        # Use existing script file
        $telegramScriptPath = Join-Path $ProjectRoot "scripts" "start_telegram_bot.py"
        
        if (-not (Test-Path $telegramScriptPath)) {
            Write-Host "❌ Telegram bot script not found: $telegramScriptPath" -ForegroundColor Red
            Write-Host "   Please create scripts/start_telegram_bot.py" -ForegroundColor Yellow
            return
        }
        
        Write-Host "✅ Using Telegram bot script: $telegramScriptPath" -ForegroundColor Gray
        & $pythonPath -u $telegramScriptPath
    } catch {
        Write-Host "❌ Hata: $_" -ForegroundColor Red
    }
}

function Start-Scheduler {
    param(
        [switch]$NoDetach,
        [switch]$Telegram,
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "STARTING SCHEDULER (DEV MODE)" "Cyan"
    
    # Start Telegram bot in background if requested
    $telegramJob = $null
    if ($Telegram) {
        Write-Host "📱 Starting Telegram bot in background..." -ForegroundColor Cyan
        
        # Use existing Telegram script file
        $telegramScriptPath = Join-Path $ProjectRoot "scripts" "start_telegram_bot.py"
        
        if (-not (Test-Path $telegramScriptPath)) {
            Write-Host "❌ Telegram bot script not found: $telegramScriptPath" -ForegroundColor Red
            Write-Host "   Skipping Telegram bot..." -ForegroundColor Yellow
        } else {
            $telegramJob = Start-Job -ScriptBlock {
                param($ProjectRoot, $ScriptPath, $VenvPath, $NoVenv)
                Set-Location $ProjectRoot
                if ($VenvPath) {
                    $pythonPath = Join-Path $VenvPath "Scripts\python.exe"
                } else {
                    $pythonPath = "python"
                }
                $env:TELEGRAM_ENABLED = "true"
                & $pythonPath -u $ScriptPath
            } -ArgumentList $ProjectRoot, $telegramScriptPath, $VenvPath, $NoVenv
            
            Start-Sleep -Seconds 2
            if ($telegramJob.State -eq "Running") {
                Write-Host "✅ Telegram bot started (background)" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Telegram bot may have failed to start" -ForegroundColor Yellow
            }
            Write-Host ""
        }
    }
    
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        
        $arguments = @("-u", "-m", "infrastructure.scheduler_runner")
        
        Write-Host "Python: $pythonPath" -ForegroundColor Cyan
        Write-Host "Environment:" -ForegroundColor Yellow
        Write-Host "  APP_ENV       = $env:APP_ENV" -ForegroundColor White
        Write-Host "  LOG_LEVEL     = $env:LOG_LEVEL" -ForegroundColor White
        Write-Host "  DEV_CONSOLE   = $env:DEV_CONSOLE" -ForegroundColor White
        if ($Telegram) {
            Write-Host "  TELEGRAM      = ENABLED" -ForegroundColor Green
        }
        Write-Host ""
        
        & $pythonPath @arguments
    } catch {
        Write-Host "❌ Hata: $_" -ForegroundColor Red
    } finally {
        # Stop Telegram bot job if running
        if ($telegramJob -and $telegramJob.State -eq "Running") {
            Write-Host ""
            Write-Host "🛑 Stopping Telegram bot..." -ForegroundColor Yellow
            Stop-Job $telegramJob
            Remove-Job $telegramJob
        }
    }
}

function Start-FullStack {
    param(
        [switch]$Telegram,
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "STARTING FULL STACK (BOT + MONITORING)" "Magenta"
    
    Write-Host "🚀 Step 1/4: Checking Docker..." -ForegroundColor Cyan
    
    # Check if Docker is running
    try {
        $null = docker ps 2>&1
        Write-Host "✅ Docker is running" -ForegroundColor Green
    } catch {
        Write-Host "❌ Docker is not running!" -ForegroundColor Red
        Write-Host "Please start Docker Desktop first." -ForegroundColor Yellow
        return
    }
    
    Write-Host ""
    Write-Host "🐳 Step 2/4: Starting monitoring containers..." -ForegroundColor Cyan
    Push-Location monitoring
    docker compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Prometheus & Grafana started" -ForegroundColor Green
        Write-Host "   - Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Gray
        Write-Host "   - Prometheus: http://localhost:9090" -ForegroundColor Gray
    } else {
        Write-Host "❌ Failed to start monitoring" -ForegroundColor Red
        Pop-Location
        return
    }
    Pop-Location
    
    # Start Telegram bot in background if requested
    $telegramJob = $null
    if ($Telegram) {
        Write-Host ""
        Write-Host "📱 Step 3/4: Starting Telegram bot..." -ForegroundColor Cyan
        
        # Load .env file if exists
        $envFile = Join-Path $ProjectRoot ".env"
        if (Test-Path $envFile) {
            Get-Content $envFile | ForEach-Object {
                if ($_ -match '^\s*([^#=]+)=(.*)$') {
                    $key = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    [Environment]::SetEnvironmentVariable($key, $value, "Process")
                }
            }
        }
        
        if ($env:TELEGRAM_BOT_TOKEN) {
            # Use existing Telegram script file
            $telegramScriptPath = Join-Path $ProjectRoot "scripts" "start_telegram_bot.py"
            
            if (-not (Test-Path $telegramScriptPath)) {
                Write-Host "❌ Telegram bot script not found: $telegramScriptPath" -ForegroundColor Red
                Write-Host "   Skipping Telegram bot..." -ForegroundColor Yellow
            } else {
                $telegramJob = Start-Job -ScriptBlock {
                    param($ProjectRoot, $ScriptPath, $VenvPath, $NoVenv)
                    Set-Location $ProjectRoot
                    if ($VenvPath) {
                        $pythonPath = Join-Path $VenvPath "Scripts\python.exe"
                    } else {
                        $pythonPath = "python"
                    }
                    $env:TELEGRAM_ENABLED = "true"
                    & $pythonPath -u $ScriptPath
                } -ArgumentList $ProjectRoot, $telegramScriptPath, $VenvPath, $NoVenv
                
                Start-Sleep -Seconds 2
                if ($telegramJob.State -eq "Running") {
                    Write-Host "✅ Telegram bot started (background)" -ForegroundColor Green
                } else {
                    Write-Host "⚠️  Telegram bot may have failed to start" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "⚠️  TELEGRAM_BOT_TOKEN not found, skipping Telegram bot" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "⏭️  Step 3/4: Telegram bot skipped (use -Telegram to enable)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "🤖 Step 4/4: Starting trading bot scheduler..." -ForegroundColor Cyan
    Write-Host ""
    
    # Start the bot
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        
        Write-Host "Python: $pythonPath" -ForegroundColor Cyan
        Write-Host "Environment:" -ForegroundColor Yellow
        Write-Host "  APP_ENV       = $env:APP_ENV" -ForegroundColor White
        Write-Host "  LOG_LEVEL     = $env:LOG_LEVEL" -ForegroundColor White
        Write-Host "  DEV_CONSOLE   = $env:DEV_CONSOLE" -ForegroundColor White
        if ($Telegram) {
            Write-Host "  TELEGRAM      = ENABLED" -ForegroundColor Green
        }
        Write-Host ""
        Write-Host "✅ Full stack is ready! Press Ctrl+C to stop..." -ForegroundColor Green
        Write-Host ""
        
        $arguments = @("-u", "-m", "infrastructure.scheduler_runner")
        & $pythonPath @arguments
    } catch {
        Write-Host "❌ Hata: $_" -ForegroundColor Red
    } finally {
        # Stop Telegram bot job if running
        if ($telegramJob -and $telegramJob.State -eq "Running") {
            Write-Host ""
            Write-Host "🛑 Stopping Telegram bot..." -ForegroundColor Yellow
            Stop-Job $telegramJob
            Remove-Job $telegramJob
        }
    }
}

function Start-Backtest {
    param(
        [string]$Days = "90",
        [string]$Symbol = "BTC-USDT"
    )
    
    Show-Banner "RUNNING BACKTEST (DEV MODE)" "Magenta"
    
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  Days   = $Days" -ForegroundColor White
    Write-Host "  Symbol = $Symbol" -ForegroundColor White
    Write-Host ""
    
    & "venv\Scripts\python.exe" -u "scripts\full_bot_backtest.py" --days $Days --symbol $Symbol
}

function Watch-Logs {
    param(
        [int]$Tail = 50,
        [switch]$Follow
    )
    
    Show-Banner "VIEWING LOGS" "Yellow"
    
    $logFile = Get-ChildItem "logs" -Filter "*.log" | 
                Sort-Object LastWriteTime -Descending | 
                Select-Object -First 1
    
    if ($logFile) {
        Write-Host "Log file: $($logFile.Name)" -ForegroundColor Cyan
        Write-Host ""
        
        if ($Follow) {
            Get-Content $logFile.FullName -Wait -Tail $Tail -Encoding UTF8 | ForEach-Object {
                $line = $_
                if ($line -match "ERROR|CRITICAL") {
                    Write-Host $line -ForegroundColor Red
                } elseif ($line -match "WARNING") {
                    Write-Host $line -ForegroundColor Yellow
                } elseif ($line -match "DEBUG") {
                    Write-Host $line -ForegroundColor Gray
                } else {
                    Write-Host $line
                }
            }
        } else {
            Get-Content $logFile.FullName -Tail $Tail -Encoding UTF8 | ForEach-Object {
                $line = $_
                if ($line -match "ERROR|CRITICAL") {
                    Write-Host $line -ForegroundColor Red
                } elseif ($line -match "WARNING") {
                    Write-Host $line -ForegroundColor Yellow
                } else {
                    Write-Host $line
                }
            }
        }
    } else {
        Write-Host "No log files found!" -ForegroundColor Red
    }
}

function Test-Health {
    param(
        [string]$VenvPath,
        [switch]$NoVenv
    )
    
    Show-Banner "HEALTH CHECK" "Green"
    
    Write-Host "Checking system health..." -ForegroundColor Yellow
    Write-Host ""
    
    # Check Python version
    try {
        $pythonPath = Get-PythonPath -VenvPath $VenvPath -NoVenv:$NoVenv
        $version = & $pythonPath --version 2>&1
        Write-Host "[OK] Python: $version ($pythonPath)" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Python: $_" -ForegroundColor Red
    }
    
    # Check Python process
    $pythonProcs = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        Write-Host "[OK] Bot Process: RUNNING (PID: $($pythonProcs.Id -join ', '))" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Bot Process: NOT RUNNING" -ForegroundColor Red
    }
    
    # Check Docker
    try {
        docker ps 2>&1 | Out-Null
        $dockerContainers = docker ps --format "{{.Names}}" 2>&1
        if ($dockerContainers -match "prometheus") {
            Write-Host "[OK] Docker: RUNNING" -ForegroundColor Green
            $dockerContainers -split "`n" | ForEach-Object {
                if ($_ -match "prometheus|grafana") {
                    Write-Host "   - $_" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "[WARN] Docker: Running but no monitoring containers" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[FAIL] Docker: NOT RUNNING" -ForegroundColor Red
    }
    
    # Check Metrics endpoint
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -UseBasicParsing -TimeoutSec 2 2>&1
        Write-Host "[OK] Metrics Endpoint: http://localhost:8000/metrics" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Metrics Endpoint: NOT RESPONDING" -ForegroundColor Red
    }
    
    # Check Prometheus
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 2 2>&1
        Write-Host "[OK] Prometheus: http://localhost:9090" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Prometheus: NOT RESPONDING" -ForegroundColor Red
    }
    
    # Check Grafana
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 2 2>&1
        Write-Host "[OK] Grafana: http://localhost:3000" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Grafana: NOT RESPONDING" -ForegroundColor Red
    }
    
    Write-Host ""
}

function Stop-Bot {
    Show-Banner "STOPPING BOT" "Red"
    
    $pythonProcs = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        $pythonProcs | Stop-Process -Force
        Write-Host "[OK] Bot processes stopped" -ForegroundColor Green
    } else {
        Write-Host "[INFO] No bot processes running" -ForegroundColor Yellow
    }
}

function Clear-Logs {
    param([int]$DaysOld = 7)
    
    Show-Banner "CLEANING OLD LOGS" "Yellow"
    
    $cutoffDate = (Get-Date).AddDays(-$DaysOld)
    $oldLogs = Get-ChildItem "logs" -Filter "*.log*" | 
                Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    if ($oldLogs) {
        Write-Host "Found $($oldLogs.Count) old log files (>$DaysOld days)" -ForegroundColor Yellow
        foreach ($log in $oldLogs) {
            Write-Host "  Removing: $($log.Name)" -ForegroundColor Gray
            Remove-Item $log.FullName -Force
        }
        Write-Host "[OK] Cleanup complete" -ForegroundColor Green
    } else {
        Write-Host "[INFO] No old logs to clean" -ForegroundColor Yellow
    }
}

function Show-Menu {
    Show-Banner "AI TRADING BOT - DEV MENU" "Cyan"
    
    Write-Host "Quick Commands:" -ForegroundColor Yellow
    Write-Host "  1. Start-Trading            - Start trading bot (scheduler mode)" -ForegroundColor White
    Write-Host "  2. Start-Trading -Once      - Single run test" -ForegroundColor White
    Write-Host "  3. Start-Scheduler          - Start scheduler only" -ForegroundColor White
    Write-Host "  4. Start-Scheduler -Telegram - Start scheduler + Telegram bot" -ForegroundColor Cyan
    Write-Host "  5. Start-FullStack          - Start Docker + Bot together 🚀" -ForegroundColor Magenta
    Write-Host "  6. Start-FullStack -Telegram - Full stack + Telegram bot 📱" -ForegroundColor Magenta
    Write-Host "  7. Start-Telegram            - Start Telegram bot only" -ForegroundColor Cyan
    Write-Host "  8. Watch-Logs -Follow       - Live log viewer" -ForegroundColor White
    Write-Host "  9. Test-Health              - System health check" -ForegroundColor White
    Write-Host " 10. Show-Python              - Show Python configuration" -ForegroundColor White
    Write-Host " 11. Install-Req              - Install requirements.txt" -ForegroundColor White
    Write-Host " 12. Stop-Bot                 - Stop bot processes" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -VenvPath <path>            - Use specific venv" -ForegroundColor Gray
    Write-Host "  -NoVenv                     - Use system Python" -ForegroundColor Gray
    Write-Host "  -Telegram                   - Enable Telegram bot (with scheduler/fullstack)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Environment:" -ForegroundColor Green
    Write-Host "  APP_ENV          = $env:APP_ENV" -ForegroundColor Gray
    Write-Host "  LOG_LEVEL        = $env:LOG_LEVEL" -ForegroundColor Gray
    Write-Host "  DEV_CONSOLE      = $env:DEV_CONSOLE" -ForegroundColor Gray
    Write-Host "  PYTHONUNBUFFERED = $env:PYTHONUNBUFFERED" -ForegroundColor Gray
    
    # Check Telegram config
    $envFile = Join-Path $ProjectRoot ".env"
    if (Test-Path $envFile) {
        $telegramToken = (Get-Content $envFile | Select-String "TELEGRAM_BOT_TOKEN").ToString() -replace 'TELEGRAM_BOT_TOKEN=', '' -replace '#.*', '' | ForEach-Object { $_.Trim() }
        if ($telegramToken) {
            Write-Host "  TELEGRAM_BOT_TOKEN = Set ✅" -ForegroundColor Green
        } else {
            Write-Host "  TELEGRAM_BOT_TOKEN = Not set ⚠️" -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

# ========================================
# AUTO-SHOW MENU
# ========================================
Show-Menu
