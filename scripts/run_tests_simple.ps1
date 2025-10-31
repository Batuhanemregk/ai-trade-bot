# AiBotBS Simple Test Runner - PowerShell Script
# Simplified test execution with basic reporting

param(
    [string]$TestType = "unit",
    [string]$Environment = "test",
    [switch]$Verbose,
    [switch]$Coverage
)

# Set error action preference
$ErrorActionPreference = "Stop"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $colorMap = @{
        "Success" = "Green"
        "Warning" = "Yellow" 
        "Error" = "Red"
        "Info" = "Cyan"
        "Header" = "Magenta"
    }
    
    $actualColor = if ($colorMap.ContainsKey($Color)) { $colorMap[$Color] } else { "White" }
    Write-Host $Message -ForegroundColor $actualColor
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
    
    # Check pytest
    try {
        $pytestVersion = python -m pytest --version 2>&1
        Write-ColorOutput "✅ pytest found: $pytestVersion" "Success"
    }
    catch {
        Write-ColorOutput "⚠️ pytest not found. Installing..." "Warning"
        pip install pytest pytest-asyncio pytest-cov pytest-mock
    }
    
    Write-ColorOutput "✅ All prerequisites met" "Success"
}

function Initialize-TestEnvironment {
    Write-ColorOutput "🚀 Initializing test environment..." "Info"
    
    # Create test directories
    $directories = @("logs", "test_reports")
    
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
            "--cov-report=html:test_reports/coverage_html",
            "--cov-report=term-missing"
        )
    }
    
    $pytestArgs += @("--html=test_reports/unit_test_report.html", "--self-contained-html")
    
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
        "--tb=short"
    )
    
    $pytestArgs += @("--html=test_reports/integration_test_report.html", "--self-contained-html")
    
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
        "--tb=short"
    )
    
    $pytestArgs += @("--html=test_reports/e2e_test_report.html", "--self-contained-html")
    
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

function New-SimpleReport {
    param(
        [hashtable]$Results
    )
    
    Write-ColorOutput "📊 Generating test report..." "Info"
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $reportFile = "test_reports/test_summary_$timestamp.md"
    
    $report = "# AiBotBS Test Report`n"
    $report += "**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"
    $report += "**Environment:** $Environment`n"
    $report += "**Test Type:** $TestType`n`n"
    
    $report += "## Test Summary`n`n"
    
    $totalPassed = 0
    $totalFailed = 0
    
    foreach ($category in $Results.Keys) {
        $result = $Results[$category]
        $status = if ($result.Passed) { "✅ PASS" } else { "❌ FAIL" }
        $duration = $result.Duration.ToString("F2")
        
        $report += "- **$category**: $status (${duration}s)`n"
        
        if ($result.Passed) {
            $totalPassed++
        } else {
            $totalFailed++
        }
    }
    
    $report += "`n## Overall Results`n`n"
    $report += "- **Total Categories:** $($Results.Count)`n"
    $report += "- **Passed:** $totalPassed ✅`n"
    $report += "- **Failed:** $totalFailed ❌`n"
    $report += "- **Success Rate:** $([math]::Round(($totalPassed / $Results.Count) * 100, 1))%`n`n"
    
    $report += "## Generated Reports`n`n"
    $report += "- Unit Tests: test_reports/unit_test_report.html`n"
    $report += "- Integration Tests: test_reports/integration_test_report.html`n"
    $report += "- E2E Tests: test_reports/e2e_test_report.html`n`n"
    
    if ($Coverage) {
        $report += "- Coverage Report: test_reports/coverage_html/index.html`n`n"
    }
    
    $report += "## Recommendations`n`n"
    
    if ($totalFailed -eq 0) {
        $report += "🎉 **Excellent!** All tests passed. System is production-ready.`n"
    } elseif ($totalFailed -le 2) {
        $report += "✅ **Good!** Minor issues need attention.`n"
    } else {
        $report += "⚠️ **Attention Required.** Several issues need fixing.`n"
    }
    
    $report | Out-File -FilePath $reportFile -Encoding UTF8
    
    Write-ColorOutput "📄 Test report saved to: $reportFile" "Success"
}

# Main execution
function Main {
    Write-ColorOutput "🚀 AiBotBS Simple Test Runner" "Header"
    Write-ColorOutput "=============================" "Header"
    
    $startTime = Get-Date
    $results = @{}
    
    try {
        # Prerequisites
        Test-Prerequisites
        
        # Initialize environment
        Initialize-TestEnvironment
        
        # Run tests based on type
        switch ($TestType.ToLower()) {
            "unit" {
                $results["Unit Tests"] = @{
                    Passed = Invoke-UnitTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "integration" {
                $results["Integration Tests"] = @{
                    Passed = Invoke-IntegrationTests
                    Duration = (Get-Date) - $startTime
                }
            }
            "e2e" {
                $results["E2E Tests"] = @{
                    Passed = Invoke-E2ETests
                    Duration = (Get-Date) - $startTime
                }
            }
            "all" {
                $testStartTime = Get-Date
                $results["Unit Tests"] = @{
                    Passed = Invoke-UnitTests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["Integration Tests"] = @{
                    Passed = Invoke-IntegrationTests
                    Duration = (Get-Date) - $testStartTime
                }
                
                $testStartTime = Get-Date
                $results["E2E Tests"] = @{
                    Passed = Invoke-E2ETests
                    Duration = (Get-Date) - $testStartTime
                }
            }
            default {
                Write-ColorOutput "❌ Invalid test type: $TestType" "Error"
                Write-ColorOutput "Valid types: unit, integration, e2e, all" "Info"
                exit 1
            }
        }
        
        # Generate report
        New-SimpleReport -Results $results
        
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
        exit 1
    }
}

# Run main function
Main
