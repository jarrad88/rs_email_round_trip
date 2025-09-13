# Email Delivery Monitor Setup Script
# Run this script as Administrator

param(
    [switch]$Install,
    [switch]$Test,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status
)

$ProjectPath = "C:\Users\Jrd\Documents\emaildeliverytime"
$ScriptName = "email_delivery_monitor.py"
$ServiceName = "EmailDeliveryMonitor"

function Write-ColorOutput($ForegroundColor) {
    if ($Host.UI.RawUI.BackgroundColor -ne $null) {
        Write-Host $args[0] -ForegroundColor $ForegroundColor
    } else {
        Write-Output $args[0]
    }
}

function Install-Dependencies {
    Write-ColorOutput Green "Installing Python dependencies..."
    
    # Check if Python is installed
    try {
        $pythonVersion = python --version 2>&1
        Write-ColorOutput Green "Found Python: $pythonVersion"
    }
    catch {
        Write-ColorOutput Red "Python is not installed or not in PATH"
        Write-ColorOutput Yellow "Please install Python 3.7+ from https://python.org"
        return $false
    }
    
    # Install dependencies
    Set-Location $ProjectPath
    try {
        pip install -r requirements.txt
        Write-ColorOutput Green "Dependencies installed successfully"
        return $true
    }
    catch {
        Write-ColorOutput Red "Failed to install dependencies: $_"
        return $false
    }
}

function Test-EmailMonitor {
    Write-ColorOutput Green "Running email delivery test..."
    
    Set-Location $ProjectPath
    try {
        python $ScriptName --test
        Write-ColorOutput Green "Test completed successfully"
    }
    catch {
        Write-ColorOutput Red "Test failed: $_"
    }
}

function Start-EmailMonitor {
    Write-ColorOutput Green "Starting email delivery monitor..."
    
    # Check if running as service
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Start-Service -Name $ServiceName
        Write-ColorOutput Green "Service started"
    }
    else {
        # Start as background process
        Set-Location $ProjectPath
        $process = Start-Process python -ArgumentList $ScriptName -PassThru -WindowStyle Hidden
        Write-ColorOutput Green "Monitor started as process ID: $($process.Id)"
        
        # Save process ID for later reference
        $process.Id | Out-File -FilePath "monitor.pid" -Encoding ASCII
    }
}

function Stop-EmailMonitor {
    Write-ColorOutput Yellow "Stopping email delivery monitor..."
    
    # Check if running as service
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq 'Running') {
        Stop-Service -Name $ServiceName
        Write-ColorOutput Green "Service stopped"
    }
    else {
        # Stop background process
        if (Test-Path "monitor.pid") {
            $pid = Get-Content "monitor.pid"
            try {
                Stop-Process -Id $pid -Force
                Remove-Item "monitor.pid"
                Write-ColorOutput Green "Monitor process stopped"
            }
            catch {
                Write-ColorOutput Yellow "Process may have already stopped"
            }
        }
        else {
            # Kill all python processes running the monitor
            Get-Process python -ErrorAction SilentlyContinue | 
                Where-Object { $_.CommandLine -like "*$ScriptName*" } | 
                Stop-Process -Force
            Write-ColorOutput Green "Monitor processes stopped"
        }
    }
}

function Get-MonitorStatus {
    Write-ColorOutput Green "Checking email delivery monitor status..."
    
    # Check service status
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-ColorOutput Green "Service Status: $($service.Status)"
    }
    
    # Check for running processes
    $processes = Get-Process python -ErrorAction SilentlyContinue | 
                 Where-Object { $_.CommandLine -like "*$ScriptName*" }
    
    if ($processes) {
        Write-ColorOutput Green "Found $($processes.Count) running monitor process(es):"
        $processes | ForEach-Object {
            Write-ColorOutput Green "  PID: $($_.Id), CPU: $($_.CPU), WorkingSet: $([math]::Round($_.WorkingSet/1MB, 2)) MB"
        }
    }
    else {
        Write-ColorOutput Yellow "No monitor processes found running"
    }
    
    # Check log file
    $logFile = Join-Path $ProjectPath "email_delivery_monitor.log"
    if (Test-Path $logFile) {
        $logInfo = Get-Item $logFile
        Write-ColorOutput Green "Log file: $($logInfo.FullName)"
        Write-ColorOutput Green "Log size: $([math]::Round($logInfo.Length/1KB, 2)) KB"
        Write-ColorOutput Green "Last modified: $($logInfo.LastWriteTime)"
        
        # Show last few log entries
        Write-ColorOutput Green "`nLast 5 log entries:"
        Get-Content $logFile -Tail 5 | ForEach-Object {
            Write-ColorOutput Cyan "  $_"
        }
    }
}

function Show-Help {
    Write-ColorOutput Green @"
Email Delivery Monitor Management Script

Usage: .\setup.ps1 [options]

Options:
  -Install    Install Python dependencies
  -Test       Run a single email delivery test
  -Start      Start the monitor (continuous mode)
  -Stop       Stop the monitor
  -Status     Show monitor status and recent logs

Examples:
  .\setup.ps1 -Install     # Install dependencies
  .\setup.ps1 -Test        # Run single test
  .\setup.ps1 -Start       # Start monitoring
  .\setup.ps1 -Status      # Check status
  .\setup.ps1 -Stop        # Stop monitoring

Configuration:
  Edit config.json to set up your Office 365 and Gmail credentials
  See README.md for detailed setup instructions

"@
}

# Main script logic
if (-not (Test-Path $ProjectPath)) {
    Write-ColorOutput Red "Project path not found: $ProjectPath"
    exit 1
}

if ($Install) {
    Install-Dependencies
}
elseif ($Test) {
    Test-EmailMonitor
}
elseif ($Start) {
    Start-EmailMonitor
}
elseif ($Stop) {
    Stop-EmailMonitor  
}
elseif ($Status) {
    Get-MonitorStatus
}
else {
    Show-Help
}
