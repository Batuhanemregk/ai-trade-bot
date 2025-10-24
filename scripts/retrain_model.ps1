# ML Model Yeniden Eğitim Scripti
# PowerShell script for manual model retraining

param(
    [string]$Frequency = "weekly",
    [switch]$RunOnce = $false,
    [switch]$ShowHistory = $false,
    [switch]$ShowNext = $false
)

# UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Start-ModelRetrain {
    Write-ColorOutput "🚀 Starting ML Model Retraining..." "Cyan"
    Write-ColorOutput "===============================================" "Cyan"
    
    # Python environment'ı aktif et
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    }
    
    # Retrain çalıştır
    if ($RunOnce) {
        Write-ColorOutput "📊 Running one-time retrain..." "Yellow"
        python -m ml.auto_retrain_scheduler --frequency $Frequency --run-once
    } else {
        Write-ColorOutput "🔄 Starting auto-retrain scheduler..." "Yellow"
        Write-ColorOutput "Frequency: $Frequency" "Green"
        Write-ColorOutput "Press Ctrl+C to stop" "Red"
        python -m ml.auto_retrain_scheduler --frequency $Frequency
    }
}

function Show-RetrainHistory {
    Write-ColorOutput "📋 Retrain History" "Cyan"
    Write-ColorOutput "=================" "Cyan"
    
    if (Test-Path "reports\retrain_history.jsonl") {
        Get-Content "reports\retrain_history.jsonl" | Select-Object -Last 10 | ForEach-Object {
            try {
                $record = $_ | ConvertFrom-Json
                $status = if ($record.status -eq "SUCCESS") { "✅" } else { "❌" }
                $time = [datetime]::Parse($record.start_time).ToString("yyyy-MM-dd HH:mm")
                Write-ColorOutput "$status $time - $($record.retrain_id) - $($record.status)" "White"
                if ($record.metrics) {
                    Write-ColorOutput "   AUC: $([math]::Round($record.metrics.auc, 3)) | Accuracy: $([math]::Round($record.metrics.accuracy, 3))" "Gray"
                }
            } catch {
                Write-ColorOutput "   Invalid record: $_" "Red"
            }
        }
    } else {
        Write-ColorOutput "No retrain history found." "Yellow"
    }
}

function Show-NextRetrain {
    Write-ColorOutput "⏰ Next Retrain Schedule" "Cyan"
    Write-ColorOutput "=======================" "Cyan"
    
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    }
    
    python -c "
from ml.auto_retrain_scheduler import AutoRetrainScheduler
scheduler = AutoRetrainScheduler('$Frequency')
print('Next retrain:', scheduler.get_next_retrain_time())
"
}

# Ana logic
if ($ShowHistory) {
    Show-RetrainHistory
} elseif ($ShowNext) {
    Show-NextRetrain
} else {
    Start-ModelRetrain
}

Write-ColorOutput "`n✅ Script completed!" "Green"

