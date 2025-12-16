# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    AI TRADING BOT - LIVE MODE LAUNCHER                       ║
# ║                         Professional Edition v2.0                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# USAGE:
#   .\run_live.ps1                    # Start bot with default settings
#   .\run_live.ps1 -NoTelegram        # Start without Telegram
#   .\run_live.ps1 -DryRun            # Paper trading mode
#   .\run_live.ps1 -Health            # Run health check only
#   .\run_live.ps1 -Logs              # Watch logs live
#   .\run_live.ps1 -Stop              # Stop running bot
#   .\run_live.ps1 -Menu              # Show interactive menu
#   .\run_live.ps1 -AutoRestart       # Auto-restart on crash

param(
    [switch]$NoTelegram,      # Disable Telegram
    [switch]$DryRun,          # Paper trading mode
    [switch]$Health,          # Health check only
    [switch]$Logs,            # Watch logs
    [switch]$Stop,            # Stop bot
    [switch]$Menu,            # Show menu
    [switch]$AutoRestart,     # Auto-restart on crash
    [switch]$NoCountdown,     # Skip countdown
    [switch]$Debug,           # Debug mode
    [switch]$UseScheduler,    # Use scheduler_runner instead of start_bot.py
    [int]$RestartDelay = 30   # Delay before restart (seconds)
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

$Script:BotName = "AI Trading Bot"
$Script:Version = "2.0.0"
$Script:LogFile = "logs/aibotbs.log"
$Script:MaxLogAgeDays = 7
$Script:CountdownSeconds = 5

# ═══════════════════════════════════════════════════════════════════════════════
# UTF-8 ENCODING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = "."
$env:LANG = "C.UTF-8"

try {
    chcp 65001 | Out-Null
    $OutputEncoding = [System.Text.UTF8Encoding]::new()
}
catch {
    Write-Host "⚠️ UTF-8 setup warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Check PowerShell version
$PSVersion = $PSVersionTable.PSVersion
if ($PSVersion.Major -lt 7) {
    Write-Host "💡 Tip: PowerShell 7+ recommended for better UTF-8 support" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATE TO PROJECT ROOT
# ═══════════════════════════════════════════════════════════════════════════════

$Script:ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Script:ProjectRoot

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

function Show-Banner {
    param(
        [string]$Title,
        [string]$Color = "Cyan",
        [switch]$Large
    )
    
    Write-Host ""
    if ($Large) {
        Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor $Color
        Write-Host "║                                                                  ║" -ForegroundColor $Color
        Write-Host "║         $($Title.PadRight(52))     ║" -ForegroundColor $Color
        Write-Host "║                                                                  ║" -ForegroundColor $Color
        Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor $Color
    }
    else {
        Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor $Color
        Write-Host " $Title" -ForegroundColor $Color
        Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor $Color
    }
    Write-Host ""
}

function Get-PythonPath {
    # Check venv locations first
    $venvLocations = @(
        ".venv\Scripts\python.exe",
        "venv\Scripts\python.exe",
        ".venv\bin\python",
        "venv\bin\python"
    )
    
    foreach ($venv in $venvLocations) {
        $fullPath = Join-Path $Script:ProjectRoot $venv
        if (Test-Path $fullPath) {
            return $fullPath
        }
    }
    
    # Try system Python
    $pythonCandidates = @("python", "python3", "py")
    foreach ($cmd in $pythonCandidates) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            return $cmd
        }
    }
    
    throw "❌ Python not found! Please install Python 3.11+ or create a virtual environment."
}

function Import-EnvFile {
    $envFile = Join-Path $Script:ProjectRoot ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*([^#=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                # Remove quotes if present
                $value = $value -replace '^["\'']', '' -replace '["\'']$', ''
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
        return $true
    }
    return $false
}

function Test-Prerequisites {
    $errors = @()
    $warnings = @()
    
    Write-Host "🔍 Running pre-flight checks..." -ForegroundColor Cyan
    Write-Host ""
    
    # 1. Python Check
    try {
        $pythonPath = Get-PythonPath
        $version = & $pythonPath --version 2>&1
        Write-Host "  ✅ Python: $version" -ForegroundColor Green
    }
    catch {
        $errors += "Python not found"
        Write-Host "  ❌ Python: NOT FOUND" -ForegroundColor Red
    }
    
    # 2. .env File Check
    if (Test-Path ".env") {
        Write-Host "  ✅ .env file: Found" -ForegroundColor Green
    }
    else {
        $errors += ".env file not found"
        Write-Host "  ❌ .env file: NOT FOUND" -ForegroundColor Red
    }
    
    # 3. API Keys Check
    if ($env:OKX_API_KEY) {
        $masked = $env:OKX_API_KEY.Substring(0, [Math]::Min(8, $env:OKX_API_KEY.Length)) + "..."
        Write-Host "  ✅ OKX API Key: $masked" -ForegroundColor Green
    }
    else {
        $errors += "OKX_API_KEY not set"
        Write-Host "  ❌ OKX API Key: NOT SET" -ForegroundColor Red
    }
    
    if ($env:OKX_API_SECRET) {
        Write-Host "  ✅ OKX Secret Key: ****" -ForegroundColor Green
    }
    else {
        $errors += "OKX_API_SECRET not set"
        Write-Host "  ❌ OKX Secret Key: NOT SET" -ForegroundColor Red
    }
    
    if ($env:OKX_API_PASSPHRASE) {
        Write-Host "  ✅ OKX Passphrase: ****" -ForegroundColor Green
    }
    else {
        $errors += "OKX_API_PASSPHRASE not set"
        Write-Host "  ❌ OKX Passphrase: NOT SET" -ForegroundColor Red
    }
    
    # 4. Telegram Check
    if ($env:TELEGRAM_BOT_TOKEN) {
        Write-Host "  ✅ Telegram Token: Set" -ForegroundColor Green
    }
    else {
        $warnings += "TELEGRAM_BOT_TOKEN not set"
        Write-Host "  ⚠️  Telegram Token: NOT SET (optional)" -ForegroundColor Yellow
    }
    
    # 5. Config Files Check
    if (Test-Path "configs/policy.yaml") {
        Write-Host "  ✅ Policy Config: Found" -ForegroundColor Green
    }
    else {
        $errors += "configs/policy.yaml not found"
        Write-Host "  ❌ Policy Config: NOT FOUND" -ForegroundColor Red
    }
    
    # 6. Models Check
    $modelCount = (Get-ChildItem "models/lgbm" -Filter "*.pkl" -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($modelCount -gt 0) {
        Write-Host "  ✅ ML Models: $modelCount models found" -ForegroundColor Green
    }
    else {
        $warnings += "No ML models found"
        Write-Host "  ⚠️  ML Models: None found (will use defaults)" -ForegroundColor Yellow
    }
    
    # 7. Logs Directory Check
    if (-not (Test-Path "logs")) {
        New-Item -ItemType Directory -Path "logs" -Force | Out-Null
        Write-Host "  ✅ Logs Directory: Created" -ForegroundColor Green
    }
    else {
        Write-Host "  ✅ Logs Directory: Exists" -ForegroundColor Green
    }
    
    # 8. Disk Space Check
    $drive = (Get-Item $Script:ProjectRoot).PSDrive
    $freeGB = [math]::Round($drive.Free / 1GB, 2)
    if ($freeGB -gt 1) {
        Write-Host "  ✅ Disk Space: ${freeGB}GB free" -ForegroundColor Green
    }
    else {
        $warnings += "Low disk space: ${freeGB}GB"
        Write-Host "  ⚠️  Disk Space: ${freeGB}GB (low!)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    
    # Summary
    if ($errors.Count -gt 0) {
        Write-Host "❌ Pre-flight check FAILED with $($errors.Count) error(s):" -ForegroundColor Red
        foreach ($err in $errors) {
            Write-Host "   • $err" -ForegroundColor Red
        }
        return $false
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "⚠️  Pre-flight check passed with $($warnings.Count) warning(s)" -ForegroundColor Yellow
    }
    else {
        Write-Host "✅ All pre-flight checks passed!" -ForegroundColor Green
    }
    
    return $true
}

function Test-Health {
    Show-Banner "SYSTEM HEALTH CHECK" "Green"
    
    $pythonPath = Get-PythonPath
    
    # 1. Python Process Check
    $pythonProcs = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        Write-Host "🤖 Bot Status: RUNNING (PID: $($pythonProcs.Id -join ', '))" -ForegroundColor Green
    }
    else {
        Write-Host "🤖 Bot Status: NOT RUNNING" -ForegroundColor Yellow
    }
    
    # 2. Exchange Connectivity (via Python)
    Write-Host ""
    Write-Host "🔌 Testing Exchange Connection..." -ForegroundColor Cyan
    
    $testScript = @"
import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

try:
    import ccxt
    exchange = ccxt.okx({
        'apiKey': os.getenv('OKX_API_KEY'),
        'secret': os.getenv('OKX_SECRET_KEY'),
        'password': os.getenv('OKX_PASSPHRASE'),
    })
    exchange.set_sandbox_mode(False)
    balance = exchange.fetch_balance()
    usdt = balance.get('USDT', {}).get('free', 0)
    print(f'OK|USDT Balance: {usdt:.2f}')
except Exception as e:
    print(f'FAIL|{str(e)[:50]}')
"@
    
    $result = & $pythonPath -c $testScript 2>&1
    if ($result -match '^OK\|(.+)$') {
        Write-Host "  ✅ Exchange: Connected - $($matches[1])" -ForegroundColor Green
    }
    else {
        $errorMsg = if ($result -match '^FAIL\|(.+)$') { $matches[1] } else { $result }
        Write-Host "  ❌ Exchange: $errorMsg" -ForegroundColor Red
    }
    
    # 3. Telegram Connectivity
    if ($env:TELEGRAM_BOT_TOKEN) {
        Write-Host ""
        Write-Host "📱 Testing Telegram Connection..." -ForegroundColor Cyan
        
        $telegramTest = @"
import os
import requests
token = os.getenv('TELEGRAM_BOT_TOKEN')
try:
    resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        if data.get('ok'):
            print(f"OK|Bot: @{data['result']['username']}")
        else:
            print(f"FAIL|{data.get('description', 'Unknown error')}")
    else:
        print(f"FAIL|HTTP {resp.status_code}")
except Exception as e:
    print(f"FAIL|{str(e)[:50]}")
"@
        
        $result = & $pythonPath -c $telegramTest 2>&1
        if ($result -match "^OK\|(.+)$") {
            Write-Host "  ✅ Telegram: $($matches[1])" -ForegroundColor Green
        }
        else {
            $errorMsg = if ($result -match "^FAIL\|(.+)$") { $matches[1] } else { $result }
            Write-Host "  ❌ Telegram: $errorMsg" -ForegroundColor Red
        }
    }
    
    # 4. Last Log Entry
    Write-Host ""
    Write-Host "📝 Recent Activity:" -ForegroundColor Cyan
    if (Test-Path $Script:LogFile) {
        $lastLines = Get-Content $Script:LogFile -Tail 3 -Encoding UTF8 -ErrorAction SilentlyContinue
        foreach ($line in $lastLines) {
            $truncated = if ($line.Length -gt 80) { $line.Substring(0, 80) + "..." } else { $line }
            Write-Host "  $truncated" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "  No log file found" -ForegroundColor Gray
    }
    
    Write-Host ""
}

function Watch-Logs {
    param(
        [int]$Tail = 50,
        [switch]$NoColor
    )
    
    Show-Banner "LIVE LOG VIEWER" "Yellow"
    
    if (-not (Test-Path $Script:LogFile)) {
        Write-Host "❌ Log file not found: $Script:LogFile" -ForegroundColor Red
        Write-Host "   Bot might not have started yet." -ForegroundColor Gray
        return
    }
    
    Write-Host "📄 Watching: $Script:LogFile" -ForegroundColor Cyan
    Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
    Write-Host ""
    
    Get-Content $Script:LogFile -Wait -Tail $Tail -Encoding UTF8 | ForEach-Object {
        $line = $_
        if ($NoColor) {
            Write-Host $line
        }
        elseif ($line -match "ERROR|CRITICAL|❌") {
            Write-Host $line -ForegroundColor Red
        }
        elseif ($line -match "WARNING|⚠️") {
            Write-Host $line -ForegroundColor Yellow
        }
        elseif ($line -match "SUCCESS|✅|✓") {
            Write-Host $line -ForegroundColor Green
        }
        elseif ($line -match "DEBUG") {
            Write-Host $line -ForegroundColor DarkGray
        }
        else {
            Write-Host $line
        }
    }
}

function Stop-Bot {
    Show-Banner "STOPPING BOT" "Red"
    
    $pythonProcs = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        Write-Host "🛑 Found $($pythonProcs.Count) Python process(es)" -ForegroundColor Yellow
        
        foreach ($proc in $pythonProcs) {
            try {
                $proc | Stop-Process -Force
                Write-Host "  ✅ Stopped PID $($proc.Id)" -ForegroundColor Green
            }
            catch {
                Write-Host "  ❌ Failed to stop PID $($proc.Id): $_" -ForegroundColor Red
            }
        }
        
        Write-Host ""
        Write-Host "✅ Bot stopped" -ForegroundColor Green
    }
    else {
        Write-Host "ℹ️  No bot processes found running" -ForegroundColor Cyan
    }
}

function Clear-OldLogs {
    param([int]$DaysOld = 7)
    
    $cutoffDate = (Get-Date).AddDays(-$DaysOld)
    $oldLogs = Get-ChildItem "logs" -Filter "*.log*" -ErrorAction SilentlyContinue | 
    Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    if ($oldLogs) {
        Write-Host "🗑️  Cleaning logs older than $DaysOld days..." -ForegroundColor Yellow
        foreach ($log in $oldLogs) {
            Remove-Item $log.FullName -Force
            Write-Host "  Removed: $($log.Name)" -ForegroundColor Gray
        }
        Write-Host "  ✅ Cleaned $($oldLogs.Count) old log file(s)" -ForegroundColor Green
    }
}

function Show-Menu {
    Clear-Host
    Show-Banner "🤖 $Script:BotName - CONTROL CENTER v$Script:Version" "Cyan" -Large
    
    Write-Host "  QUICK ACTIONS:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    1. 🚀 Start Bot (LIVE)         - Start live trading" -ForegroundColor White
    Write-Host "    2. 🧪 Start Bot (DRY-RUN)      - Paper trading mode" -ForegroundColor White
    Write-Host "    3. 📊 Start with Scheduler     - Use scheduler_runner" -ForegroundColor White
    Write-Host "    4. 🔄 Start with Auto-Restart  - Auto-restart on crash" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  MONITORING:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    5. 💓 Health Check             - Check system status" -ForegroundColor White
    Write-Host "    6. 📝 Watch Logs               - Live log viewer" -ForegroundColor White
    Write-Host "    7. 🛑 Stop Bot                 - Stop running bot" -ForegroundColor Red
    Write-Host ""
    Write-Host "  MAINTENANCE:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    8. 🗑️  Clean Old Logs          - Remove logs > 7 days" -ForegroundColor White
    Write-Host "    9. 🔧 Run Pre-flight Checks    - Verify configuration" -ForegroundColor White
    Write-Host "    0. 🚪 Exit                     - Exit menu" -ForegroundColor Gray
    Write-Host ""
    
    $choice = Read-Host "  Select option (0-9)"
    
    switch ($choice) {
        "1" { Start-TradingBot -Live }
        "2" { Start-TradingBot -DryRun }
        "3" { Start-TradingBot -Live -UseScheduler }
        "4" { Start-TradingBot -Live -UseScheduler -AutoRestart }
        "5" { Test-Health; Read-Host "Press Enter to continue" }
        "6" { Watch-Logs }
        "7" { Stop-Bot; Read-Host "Press Enter to continue" }
        "8" { Clear-OldLogs; Read-Host "Press Enter to continue" }
        "9" { 
            Import-EnvFile | Out-Null
            Test-Prerequisites
            Read-Host "Press Enter to continue"
        }
        "0" { return }
        default { Write-Host "Invalid option" -ForegroundColor Red; Start-Sleep 1 }
    }
    
    Show-Menu
}

function Start-TradingBot {
    param(
        [switch]$Live,
        [switch]$DryRun,
        [switch]$NoTelegram,
        [switch]$UseScheduler,
        [switch]$AutoRestart,
        [switch]$NoCountdown
    )
    
    # Load environment
    if (-not (Import-EnvFile)) {
        Write-Host "❌ .env file not found!" -ForegroundColor Red
        return
    }
    
    # Set environment variables
    if ($Live -and -not $DryRun) {
        $env:TRADING_LIVE = 'true'
        $env:APP_ENV = 'prod'
        $modeText = "🔴 LIVE TRADING"
        $modeColor = "Red"
    }
    else {
        $env:TRADING_LIVE = 'false'
        $env:APP_ENV = 'dev'
        $modeText = "🧪 DRY-RUN (Paper Trading)"
        $modeColor = "Yellow"
    }
    
    if ($NoTelegram) {
        $env:TELEGRAM_ENABLED = 'false'
    }
    else {
        $env:TELEGRAM_ENABLED = 'true'
    }
    
    $env:LOG_LEVEL = if ($Debug) { 'DEBUG' } else { 'INFO' }
    $env:LOG_EMOJI = '1'
    $env:CONSOLE_LOG = '1'
    
    # Show banner
    Show-Banner "$modeText MODE" $modeColor -Large
    
    # Run pre-flight checks
    if (-not (Test-Prerequisites)) {
        Write-Host ""
        Write-Host "❌ Pre-flight checks failed. Fix the issues above and try again." -ForegroundColor Red
        return
    }
    
    Write-Host ""
    
    # Configuration display
    Write-Host "📊 Configuration:" -ForegroundColor Yellow
    Write-Host "   • Trading Mode  : $modeText" -ForegroundColor $(if ($Live) { "Red" } else { "Yellow" })
    Write-Host "   • Telegram      : $(if ($NoTelegram) { 'DISABLED ❌' } else { 'ENABLED ✅' })" -ForegroundColor $(if ($NoTelegram) { "Yellow" } else { "Green" })
    Write-Host "   • Log Level     : $env:LOG_LEVEL" -ForegroundColor Cyan
    Write-Host "   • Auto-Restart  : $(if ($AutoRestart) { 'ENABLED ✅' } else { 'DISABLED' })" -ForegroundColor $(if ($AutoRestart) { "Green" } else { "Gray" })
    Write-Host "   • Scheduler     : $(if ($UseScheduler) { 'scheduler_runner' } else { 'start_bot.py' })" -ForegroundColor Cyan
    Write-Host ""
    
    # Get Python path
    $pythonPath = Get-PythonPath
    Write-Host "🐍 Python: $pythonPath" -ForegroundColor Cyan
    Write-Host ""
    
    # Warning for LIVE mode
    if ($Live -and -not $DryRun) {
        Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Red
        Write-Host "⚠️  WARNING: LIVE TRADING MODE - REAL MONEY AT RISK! ⚠️" -ForegroundColor Red
        Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Red
        Write-Host ""
    }
    
    # Countdown
    if (-not $NoCountdown) {
        Write-Host "Starting in $Script:CountdownSeconds seconds... Press Ctrl+C to cancel" -ForegroundColor Yellow
        for ($i = $Script:CountdownSeconds; $i -gt 0; $i--) {
            Write-Host "$i..." -ForegroundColor Yellow -NoNewline
            Start-Sleep -Seconds 1
        }
        Write-Host ""
        Write-Host ""
    }
    
    # Clean old logs
    Clear-OldLogs -DaysOld $Script:MaxLogAgeDays
    Write-Host ""
    
    # Start bot
    Write-Host "🚀 Starting $Script:BotName..." -ForegroundColor Green
    Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
    Write-Host ""
    
    # Bot execution handled in AutoRestart block or single-run block below
    
    if ($AutoRestart) {
        $restartCount = 0
        while ($true) {
            $restartCount++
            $startTime = Get-Date
            
            Write-Host "▶️  Starting bot (attempt #$restartCount)..." -ForegroundColor Cyan
            
            try {
                if ($UseScheduler) {
                    & $pythonPath -u -m infrastructure.scheduler_runner
                }
                else {
                    & $pythonPath -u start_bot.py
                }
                $exitCode = $LASTEXITCODE
            }
            catch {
                $exitCode = 1
            }
            
            $runTime = (Get-Date) - $startTime
            
            if ($exitCode -eq 0) {
                Write-Host "✅ Bot exited cleanly" -ForegroundColor Green
                break
            }
            
            Write-Host ""
            Write-Host "⚠️  Bot crashed after $($runTime.ToString('hh\:mm\:ss'))" -ForegroundColor Yellow
            Write-Host "   Exit code: $exitCode" -ForegroundColor Gray
            Write-Host "   Restarting in $RestartDelay seconds... (Ctrl+C to abort)" -ForegroundColor Yellow
            Write-Host ""
            
            Start-Sleep -Seconds $RestartDelay
        }
    }
    else {
        try {
            if ($UseScheduler) {
                & $pythonPath -u -m infrastructure.scheduler_runner
            }
            else {
                & $pythonPath -u start_bot.py
            }
        }
        catch {
            Write-Host "❌ Bot crashed: $_" -ForegroundColor Red
            exit 1
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

# Handle command-line switches
if ($Menu) {
    Show-Menu
    exit 0
}

if ($Health) {
    Import-EnvFile | Out-Null
    Test-Health
    exit 0
}

if ($Logs) {
    Watch-Logs
    exit 0
}

if ($Stop) {
    Stop-Bot
    exit 0
}

# Default: Start the bot
$params = @{
    Live         = -not $DryRun
    DryRun       = $DryRun
    NoTelegram   = $NoTelegram
    UseScheduler = $UseScheduler
    AutoRestart  = $AutoRestart
    NoCountdown  = $NoCountdown
}

Start-TradingBot @params
