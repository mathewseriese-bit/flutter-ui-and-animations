# Start Guardian - Single Source of Truth for Service Orchestration
# This is the RECOMMENDED way to start all services

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "System Guardian - Service Orchestrator" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Get the root directory (Auralis_App)
$rootDir = $PSScriptRoot

# Find virtual environment
$venvPython = $null
$venvPaths = @(
    "$rootDir\.venv\Scripts\python.exe",
    "$rootDir\venv\Scripts\python.exe"
)

foreach ($path in $venvPaths) {
    if (Test-Path $path) {
        $venvPython = $path
        Write-Host "Found Python at: $venvPython" -ForegroundColor Green
        break
    }
}

if (-not $venvPython) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Check if Guardian is already running
$guardianPort = 9000
$connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | 
               Where-Object { $_.LocalPort -eq $guardianPort }

if ($connections) {
    Write-Host "WARNING: Guardian appears to be already running on port $guardianPort" -ForegroundColor Yellow
    $process = Get-Process -Id $connections[0].OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "  PID: $($process.Id), Name: $($process.Name)" -ForegroundColor Yellow
    }
    Write-Host ""
    $response = Read-Host "Do you want to continue anyway? (yes/no)"
    if ($response -ne "yes") {
        Write-Host "Exiting. Use stop_all_services.ps1 to stop the existing Guardian." -ForegroundColor Cyan
        exit
    }
}

# Path to Guardian script
$guardianScript = Join-Path $rootDir "backend\services\system_guardian\guardian.py"

if (-not (Test-Path $guardianScript)) {
    Write-Host "ERROR: Guardian script not found at: $guardianScript" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting System Guardian..." -ForegroundColor Cyan
Write-Host "  - Will start all services in proper order" -ForegroundColor Gray
Write-Host "  - Will monitor service health" -ForegroundColor Gray
Write-Host "  - Will auto-restart failed services" -ForegroundColor Gray
Write-Host "  - Will prevent duplicate launches" -ForegroundColor Gray
Write-Host ""
Write-Host "Guardian will run in this window. Press Ctrl+C to stop all services." -ForegroundColor Yellow
Write-Host ""

# Start Guardian
try {
    & $venvPython $guardianScript
} catch {
    Write-Host ""
    Write-Host "ERROR: Guardian failed to start: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Guardian stopped." -ForegroundColor Yellow
