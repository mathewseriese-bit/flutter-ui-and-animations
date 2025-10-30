# Manual Service Launcher - DEPRECATED
# This script is kept for reference but should NOT be used
# Use start_guardian.ps1 instead for proper service orchestration

Write-Host "===============================================" -ForegroundColor Yellow
Write-Host "WARNING: This script is DEPRECATED" -ForegroundColor Red
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "This manual launcher can cause duplicate service launches." -ForegroundColor Yellow
Write-Host "Please use start_guardian.ps1 instead for proper orchestration." -ForegroundColor Yellow
Write-Host ""
Write-Host "The Guardian provides:" -ForegroundColor Cyan
Write-Host "  - Single source of truth for service status" -ForegroundColor Cyan
Write-Host "  - Prevents duplicate launches" -ForegroundColor Cyan
Write-Host "  - Automatic health monitoring" -ForegroundColor Cyan
Write-Host "  - Proper service recovery" -ForegroundColor Cyan
Write-Host ""
$response = Read-Host "Do you want to continue anyway? (yes/no)"

if ($response -ne "yes") {
    Write-Host "Exiting. Please run: .\start_guardian.ps1" -ForegroundColor Green
    exit
}

Write-Host ""
Write-Host "Starting services manually..." -ForegroundColor Yellow

# Get the root directory (Auralis_App)
$rootDir = Split-Path -Parent $PSScriptRoot

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
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Service configurations
$services = @(
    @{Name="Character Extraction"; Path="backend\services\character_extraction\service.py"; Port=8001},
    @{Name="Document Processor"; Path="backend\services\document_processor\service.py"; Port=8002},
    @{Name="Query Engine"; Path="backend\services\query_engine\service.py"; Port=8003},
    @{Name="Metadata Service"; Path="backend\services\metadata_service\service.py"; Port=8004},
    @{Name="RAG Service"; Path="backend\services\rag_service\service.py"; Port=8005}
)

# Function to check if port is in use
function Test-PortInUse {
    param([int]$Port)
    
    $connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | 
                   Where-Object { $_.LocalPort -eq $Port }
    
    return $connections.Count -gt 0
}

# Start each service
foreach ($service in $services) {
    $servicePath = Join-Path $rootDir $service.Path
    
    if (-not (Test-Path $servicePath)) {
        Write-Host "ERROR: Service script not found: $servicePath" -ForegroundColor Red
        continue
    }
    
    # Check if port is already in use
    if (Test-PortInUse -Port $service.Port) {
        Write-Host "WARNING: Port $($service.Port) is already in use. Skipping $($service.Name)" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "Starting $($service.Name) on port $($service.Port)..." -ForegroundColor Cyan
    
    # Start in new window
    Start-Process -FilePath $venvPython -ArgumentList $servicePath `
                  -WorkingDirectory $rootDir -WindowStyle Normal
    
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "Services started. Check individual windows for status." -ForegroundColor Green
Write-Host ""
Write-Host "REMINDER: Use stop_all_services.ps1 to stop all services" -ForegroundColor Yellow
Write-Host "Or use the Guardian for proper management: start_guardian.ps1" -ForegroundColor Cyan
