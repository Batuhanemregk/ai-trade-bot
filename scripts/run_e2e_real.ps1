#!/usr/bin/env pwsh
<#
.SYNOPSIS
    E2E Real Trading Test Runner - PowerShell Script
    
.DESCRIPTION
    Gerçek OKX API'leri ile uçtan uca test koşucu.
    Mock kullanmaz, gerçek verilerle test eder.
    
.PARAMETER Mode
    Trading mode: paper or live (default: paper)
    
.PARAMETER Symbols
    Test symbols (comma-separated) (default: BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP)
    
.PARAMETER Timeframes
    Test timeframes (comma-separated) (default: 5m,15m,1h)
    
.PARAMETER Duration
    Test duration in minutes (default: 30)
    
.PARAMETER FailFast
    Stop on first critical error
    
.PARAMETER Verbose
    Verbose logging
    
.PARAMETER ConfigFile
    Environment configuration file (default: .env.e2e)
    
.EXAMPLE
    .\run_e2e_real.ps1 -Mode paper -Duration 20
    
.EXAMPLE
    .\run_e2e_real.ps1 -Mode paper -Symbols "BTC-USDT-SWAP,ETH-USDT-SWAP" -Verbose
    
.EXAMPLE
    .\run_e2e_real.ps1 -Mode live -Duration 60 -FailFast
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("paper", "live")]
    [string]$Mode = "paper",
    
    [Parameter(Mandatory=$false)]
    [string]$Symbols = "BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP",
    
    [Parameter(Mandatory=$false)]
    [string]$Timeframes = "5m,15m,1h",
    
    [Parameter(Mandatory=$false)]
    [int]$Duration = 30,
    
    [Parameter(Mandatory=$false)]
    [switch]$FailFast,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigFile = ".env.e2e"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Script configuration
$ScriptName = "E2E Real Trading Test"
$ScriptVersion = "1.0.0"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$E2ERunner = Join-Path $ProjectRoot "tests\e2e\e2e_real_runner.py"
$ReportsDir = Join-Path $ProjectRoot "reports\e2e"
$LogsDir = Join-Path $ReportsDir "logs"

# Color functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✅ $Message" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠️ $Message" "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "❌ $Message" "Red"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "ℹ️ $Message" "Cyan"
}

# Main function
function Main {
    try {
        Write-ColorOutput "🚀 $ScriptName v$ScriptVersion" "Magenta"
        Write-ColorOutput "=" * 50 "Magenta"
        
        # Validate parameters
        Write-Info "Validating parameters..."
        if ($Duration -lt 5 -or $Duration -gt 120) {
            throw "Duration must be between 5 and 120 minutes"
        }
        
        if ($Mode -eq "live" -and -not $FailFast) {
            Write-Warning "Live mode detected - consider using -FailFast for safety"
        }
        
        # Check if Python is available
        Write-Info "Checking Python installation..."
        try {
            $pythonVersion = python --version 2>&1
            Write-Success "Python found: $pythonVersion"
        }
        catch {
            throw "Python not found. Please install Python 3.8+ and ensure it's in PATH"
        }
        
        # Check if E2E runner exists
        Write-Info "Checking E2E runner..."
        if (-not (Test-Path $E2ERunner)) {
            throw "E2E runner not found: $E2ERunner"
        }
        Write-Success "E2E runner found"
        
        # Create reports directory
        Write-Info "Creating reports directory..."
        if (-not (Test-Path $ReportsDir)) {
            New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
        }
        if (-not (Test-Path $LogsDir)) {
            New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
        }
        Write-Success "Reports directory created: $ReportsDir"
        
        # Load environment configuration
        Write-Info "Loading environment configuration..."
        $envFile = Join-Path $ProjectRoot $ConfigFile
        if (Test-Path $envFile) {
            Write-Success "Environment file found: $envFile"
            # Load environment variables from file
            Get-Content $envFile | ForEach-Object {
                if ($_ -match '^([^#][^=]+)=(.*)$') {
                    $name = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    [Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
        else {
            Write-Warning "Environment file not found: $envFile (using system environment variables)"
        }
        
        # Validate required environment variables
        Write-Info "Validating environment variables..."
        $requiredVars = @("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")
        $missingVars = @()
        
        foreach ($var in $requiredVars) {
            if (-not [Environment]::GetEnvironmentVariable($var)) {
                $missingVars += $var
            }
        }
        
        if ($missingVars.Count -gt 0) {
            throw "Missing required environment variables: $($missingVars -join ', ')"
        }
        Write-Success "Environment variables validated"
        
        # Build command arguments
        Write-Info "Building command arguments..."
        $commandArgs = @(
            $E2ERunner
            "--mode", $Mode
            "--symbols", $Symbols
            "--timeframes", $Timeframes
            "--duration", $Duration.ToString()
        )
        
        if ($FailFast) {
            $commandArgs += "--fail-fast"
        }
        
        if ($Verbose) {
            $commandArgs += "--verbose"
        }
        
        $commandLine = "python " + ($commandArgs -join " ")
        Write-Info "Command: $commandLine"
        
        # Change to project root directory
        Set-Location $ProjectRoot
        
        # Run E2E test
        Write-Info "Starting E2E test..."
        Write-ColorOutput "Mode: $Mode" "White"
        Write-ColorOutput "Symbols: $Symbols" "White"
        Write-ColorOutput "Timeframes: $Timeframes" "White"
        Write-ColorOutput "Duration: $Duration minutes" "White"
        Write-ColorOutput "Fail Fast: $($FailFast.IsPresent)" "White"
        Write-ColorOutput "Verbose: $($Verbose.IsPresent)" "White"
        Write-ColorOutput ""
        
        $startTime = Get-Date
        
        # Execute the E2E runner
        $process = Start-Process -FilePath "python" -ArgumentList $commandArgs -NoNewWindow -PassThru -Wait
        
        $endTime = Get-Date
        $duration = $endTime - $startTime
        
        # Check exit code
        if ($process.ExitCode -eq 0) {
            Write-Success "E2E test completed successfully!"
            Write-Info "Duration: $($duration.TotalSeconds.ToString('F1')) seconds"
            
            # Show report location
            $reportFile = Join-Path $ReportsDir "E2E_REPORT.md"
            if (Test-Path $reportFile) {
                Write-Success "Report generated: $reportFile"
            }
            
            # Show artifacts
            Write-Info "Generated artifacts:"
            Get-ChildItem $ReportsDir -File | ForEach-Object {
                Write-ColorOutput "  - $($_.Name)" "White"
            }
            
            return 0
        }
        else {
            Write-Error "E2E test failed with exit code: $($process.ExitCode)"
            Write-Info "Duration: $($duration.TotalSeconds.ToString('F1')) seconds"
            
            # Show log file if it exists
            $logFile = Join-Path $LogsDir "e2e_test.log"
            if (Test-Path $logFile) {
                Write-Info "Check log file for details: $logFile"
            }
            
            return $process.ExitCode
        }
    }
    catch {
        Write-Error "Script execution failed: $($_.Exception.Message)"
        Write-Error "Stack trace: $($_.ScriptStackTrace)"
        return 1
    }
}

# Cleanup function
function Cleanup {
    Write-Info "Cleaning up..."
    # Any cleanup tasks can be added here
}

# Error handling
trap {
    Write-Error "Unexpected error: $($_.Exception.Message)"
    Cleanup
    exit 1
}

# Run main function
$exitCode = Main

# Cleanup
Cleanup

# Exit with appropriate code
exit $exitCode
