# Run Telegram bot tests (PowerShell)
# Usage: .\scripts\ci_tg.ps1 [test_file]

param(
    [string]$TestFile = ""
)

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Change to project root
Set-Location $ProjectRoot

# Check if pytest is available
if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
    Write-Host "pytest not found. Installing..."
    pip install pytest pytest-asyncio
}

# Run Telegram tests
if ([string]::IsNullOrEmpty($TestFile)) {
    Write-Host "Running all Telegram tests..."
    pytest tests/telegram/ -v --tb=short
} else {
    Write-Host "Running specific test: $TestFile"
    pytest $TestFile -v --tb=short
}

Write-Host "✅ Telegram tests completed"

