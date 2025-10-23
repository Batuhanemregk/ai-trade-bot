# AiBotBS Test Runner - PowerShell Script
# Comprehensive test execution with detailed reporting

param(
    [string]$TestType = "all",
    [string]$Environment = "test",
    [switch]$Verbose,
    [switch]$Coverage,
    [switch]$Parallel,
    [string]$ConfigFile = "test_config.json",
    [string]$OutputDir = "test_reports"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Header = "Magenta"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Test-Prerequisites {
    Write-ColorOutput "🔍 Checking prerequisites..." "Info"
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-ColorOutput "✅ Python found: $pythonVersion" "Success"
    }
    catch {
        Write-ColorOutput "❌ Python not found. Please install Python 3.8+" "Error"
        exit 1
    }
    
    # Check pip
    try {
        $pipVersion = pip --version 2>&1
        Write-ColorOutput "✅ pip found: $pipVersion" "Success"
    }
    catch {
        Write-ColorOutput "❌ pip not found. Please install pip" "Error"
        exit 1
    }
    
    # Check pytest
    try {
        $pytestVersion = python -m pytest --version 2>&1
        Write-ColorOutput "✅ pytest found: $pytestVersion" "Success"
    }
    catch {
        Write-ColorOutput "⚠️ pytest not found. Installing..." "Warning"
        pip install pytest pytest-asyncio pytest-cov pytest-mock
    }
    
    # Check if we're in the right directory
    if (-not (Test-Path "main.py")) {
        Write-ColorOutput "❌ Not in AiBotBS root directory. Please run from project root." "Error"
        exit 1
    }
    
    Write-ColorOutput "✅ All prerequisites met" "Success"
}

function Initialize-TestEnvironment {
    Write-ColorOutput "🚀 Initializing test environment..." "Info"
    
    # Create test directories
    $directories = @("logs", "test_reports", "tests/unit", "tests/integration", "tests/e2e", "tests/performance", "tests/security", "tests/config")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-ColorOutput "📁 Created directory: $dir" "Info"
        }
    }
    
    # Set environment variables
    $env:APP_ENV = $Environment
    $env:LOG_LEVEL = if ($Verbose) { "DEBUG" } else { "INFO" }
    $env:OKX_SANDBOX = "true"
    $env:OKX_TESTNET = "true"
    $env:NEWS_VERBOSITY = "full"
    $env:PYTHONPATH = (Get-Location).Path
    $env:PYTHONUNBUFFERED = "1"
    
    Write-ColorOutput "✅ Test environment initialized" "Success"
}

function Install-TestDependencies {
    Write-ColorOutput "📦 Installing test dependencies..." "Info"
    
    $dependencies = @(
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0",
        "pytest-xdist>=3.0.0",
        "pytest-html>=3.1.0",
        "pytest-json-report>=1.5.0"
    )
    
    foreach ($dep in $dependencies) {
        try {
            pip install $dep --quiet
            Write-ColorOutput "✅ Installed: $dep" "Success"
        }
        catch {
            Write-ColorOutput "⚠️ Failed to install: $dep" "Warning"
        }
    }
}

function Invoke-UnitTests {
    Write-ColorOutput "🧪 Running Unit Tests..." "Header"
    
    $pytestArgs = @(
        "tests/unit/",
        "-v",
        "--tb=short"
    )
    
    if ($Coverage) {
        $pytestArgs += @(
            "--cov=application",
            "--cov=scoring", 
            "--cov=adapters",
            "--cov-report=html:$OutputDir/coverage_html",
            "--cov-report=term-missing",
            "--cov-report=json:$OutputDir/coverage.json"
        )
    }
    
    if ($Parallel) {
        $pytestArgs += @("-n", "auto")
    }
    
    $pytestArgs += @("--html=$OutputDir/unit_test_report.html", "--self-contained-html")
    
    try {
        python -m pytest @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Unit tests passed" "Success"
            return $true
        } else {
            Write-ColorOutput "❌ Unit tests failed" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "💥 Unit tests crashed: $_" "Error"
        return $false
    }
}

function Invoke-IntegrationTests {
    Write-ColorOutput "🔗 Running Integration Tests..." "Header"
    
    $pytestArgs = @(
        "tests/integration/",
        "-v",
        "--tb=short",
        "--env=$Environment"
    )
    
    if ($Parallel) {
        $pytestArgs += @("-n", "2")  # Limit parallel for integration tests
    }
    
    $pytestArgs += @("--html=$OutputDir/integration_test_report.html", "--self-contained-html")
    
    try {
        python -m pytest @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Integration tests passed" "Success"
            return $true
        } else {
            Write-ColorOutput "❌ Integration tests failed" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "💥 Integration tests crashed: $_" "Error"
        return $false
    }
}

function Invoke-E2ETests {
    Write-ColorOutput "🎯 Running End-to-End Tests..." "Header"
    
    $pytestArgs = @(
        "tests/e2e/",
        "-v",
        "--tb=short",
        "--env=$Environment"
    )
    
    $pytestArgs += @("--html=$OutputDir/e2e_test_report.html", "--self-contained-html")
    
    try {
        python -m pytest @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ E2E tests passed" "Success"
            return $true
        } else {
            Write-ColorOutput "❌ E2E tests failed" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "💥 E2E tests crashed: $_" "Error"
        return $false
    }
}

function Invoke-PerformanceTests {
    Write-ColorOutput "⚡ Running Performance Tests..." "Header"
    
    $pytestArgs = @(
        "tests/performance/",
        "-v",
        "--tb=short",
        "--env=$Environment"
    )
    
    $pytestArgs += @("--html=$OutputDir/performance_test_report.html", "--self-contained-html")
    
    try {
        $result = python -m pytest @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Performance tests passed" "Success"
            return $true
        } else {
            Write-ColorOutput "❌ Performance tests failed" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "💥 Performance tests crashed: $_" "Error"
        return $false
    }
}

function Invoke-SecurityTests {
    Write-ColorOutput "🔒 Running Security Tests..." "Header"
    
    $pytestArgs = @(
        "tests/security/",
        "-v",
        "--tb=short",
        "--env=$Environment"
    )
    
    $pytestArgs += @("--html=$OutputDir/security_test_report.html", "--self-contained-html")
    
    try {
        $result = python -m pytest @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Security tests passed" "Success"
            return $true
        } else {
            Write-ColorOutput "❌ Security tests failed" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "💥 Security tests crashed: $_" "Error"
        return $false
    }
}

function Invoke-ConfigTests {
    Write-ColorOutput "⚙️ Running Configuration Tests..." "Header"
    
    $pytestArgs = @(
        "tests/config/",
        "-v",
        "--tb=short",
        "--env=$Environment"
    )
    
    $pytestArgs += @("--html=$OutputDir/config_test_report.html", "--self-contained-html")
    
    try {
        $result = python -m pytest @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Configuration tests passed" "Success"
            return $true
        } else {
            Write-ColorOutput "❌ Configuration tests failed" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "💥 Configuration tests crashed: $_" "Error"
        return $false
    }
}

function New-TestReport {
    param(
        [hashtable]$Results
    )
    
    Write-ColorOutput "📊 Generating test report..." "Info"
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $reportFile = "$OutputDir/test_summary_$timestamp.md"
    
    $report = @"
# AiBotBS Test Report

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Environment:** $Environment
**Test Type:** $TestType

## 📊 Test Summary

"@

    $totalPassed = 0
    $totalFailed = 0
    
    $report += "`n"
    $report += "| Test Category | Status | Duration |`n"
    $report += "|---------------|--------|----------|`n"
    
    foreach ($category in $Results.Keys) {
        $result = $Results[$category]
        $status = if ($result.Passed) { "✅ PASS" } else { "❌ FAIL" }
        $duration = $result.Duration.ToString("F2")
        
        $report += "| $category | $status | ${duration}s |`n"
        
        if ($result.Passed) {
            $totalPassed++
        } else {
            $totalFailed++
        }
    }
    
    $report += @"

## 📈 Overall Results

- **Total Categories:** $($Results.Count)
- **Passed:** $totalPassed ✅
- **Failed:** $totalFailed ❌
- **Success Rate:** $([math]::Round(($totalPassed / $Results.Count) * 100, 1))%

## 📁 Generated Reports

- Unit Tests: `$OutputDir/unit_test_report.html`
- Integration Tests: `$OutputDir/integration_test_report.html`
- E2E Tests: `$OutputDir/e2e_test_report.html`
- Performance Tests: `$OutputDir/performance_test_report.html`
- Security Tests: `$OutputDir/security_test_report.html`
- Configuration Tests: `$OutputDir/config_test_report.html`

"@

    if ($Coverage) {
        $report += @"
- Coverage Report: `$OutputDir/coverage_html/index.html`
- Coverage JSON: `$OutputDir/coverage.json`

"@
    }
    
    $report += @"

## 🎯 Recommendations

"@

    if ($totalFailed -eq 0) {
        $report += "🎉 **Excellent!** All tests passed. System is production-ready."
    } elseif ($totalFailed -le 2) {
        $report += "✅ **Good!** Minor issues need attention."
    } else {
        $report += "⚠️ **Attention Required.** Several issues need fixing."
    }
    
    $report | Out-File -FilePath $reportFile -Encoding UTF8
    
    Write-ColorOutput "📄 Test report saved to: $reportFile" "Success"
    
    # Open report in browser if on Windows
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        try {
            Start-Process $reportFile
        }
        catch {
            Write-ColorOutput "⚠️ Could not open report automatically" "Warning"
        }
    }
}

function Remove-TestEnvironment {
    Write-ColorOutput "🧹 Cleaning up test environment..." "Info"
    
    # Clean up temporary files
    $tempFiles = @("*.pyc", "__pycache__", ".pytest_cache", ".coverage")
    
    foreach ($pattern in $tempFiles) {
        Get-ChildItem -Path . -Recurse -Name $pattern -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-ColorOutput "✅ Cleanup completed" "Success"
}

# Main execution
function Main {
    Write-ColorOutput "🚀 AiBotBS Comprehensive Test Runner" "Header"
    Write-ColorOutput "=====================================" "Header"
    
    $startTime = Get-Date
    $results = @{}
    
    try {
        # Prerequisites
        Test-Prerequisites
        
        # Initialize environment
        Initialize-TestEnvironment
        
        # Install dependencies
        Install-TestDependencies
        
        # Run tests based on type
        switch ($TestType.ToLower()) {
            "unit" {
                $results["Unit Tests"] = @{
                    Passed = Run-UnitTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "integration" {
                $results["Integration Tests"] = @{
                    Passed = Run-IntegrationTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "e2e" {
                $results["E2E Tests"] = @{
                    Passed = Run-E2ETests
                    Duration = (Get-Date) - $startTime
                }
            }
            "performance" {
                $results["Performance Tests"] = @{
                    Passed = Run-PerformanceTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "security" {
                $results["Security Tests"] = @{
                    Passed = Run-SecurityTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "config" {
                $results["Configuration Tests"] = @{
                    Passed = Run-ConfigTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "all" {
                $testStartTime = Get-Date
                $results["Unit Tests"] = @{
                    Passed = Run-UnitTests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["Integration Tests"] = @{
                    Passed = Run-IntegrationTests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["E2E Tests"] = @{
                    Passed = Run-E2ETests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["Performance Tests"] = @{
                    Passed = Run-PerformanceTests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["Security Tests"] = @{
                    Passed = Run-SecurityTests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["Configuration Tests"] = @{
                    Passed = Run-ConfigTests
                    Duration = (Get-Date) - $testStartTime
                }
            }
            default {
                Write-ColorOutput "❌ Invalid test type: $TestType" "Error"
                Write-ColorOutput "Valid types: unit, integration, e2e, performance, security, config, all" "Info"
                exit 1
            }
        }
        
        # Generate report
        Generate-TestReport -Results $results
        
        # Cleanup
        Cleanup-TestEnvironment
        
        # Final summary
        $totalDuration = (Get-Date) - $startTime
        $passedCount = ($results.Values | Where-Object { $_.Passed }).Count
        $totalCount = $results.Count
        
        Write-ColorOutput "`n🎯 Test Execution Complete!" "Header"
        Write-ColorOutput "=============================" "Header"
        Write-ColorOutput "Total Duration: $($totalDuration.ToString('F2'))s" "Info"
        Write-ColorOutput "Tests Passed: $passedCount/$totalCount" "Info"
        Write-ColorOutput "Success Rate: $([math]::Round(($passedCount / $totalCount) * 100, 1))%" "Info"
        
        if ($passedCount -eq $totalCount) {
            Write-ColorOutput "🎉 All tests passed! System is ready for production." "Success"
            exit 0
        } else {
            Write-ColorOutput "⚠️ Some tests failed. Please review the reports." "Warning"
            exit 1
        }
    }
    catch {
        Write-ColorOutput "💥 Test execution failed: $_" "Error"
        Write-ColorOutput "Stack trace: $($_.ScriptStackTrace)" "Error"
        exit 1
    }
}

# Run main function
Main
