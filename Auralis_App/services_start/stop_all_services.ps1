# Stop All Services Script
# Stops all running services (both manually started and Guardian-managed)

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Stopping All Services" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Service ports to check
$ports = @(8001, 8002, 8003, 8004, 8005, 9000)

Write-Host "Searching for processes using service ports..." -ForegroundColor Yellow

$processesFound = $false

foreach ($port in $ports) {
    # Find processes using the port
    $connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | 
                   Where-Object { $_.LocalPort -eq $port }
    
    foreach ($conn in $connections) {
        $processesFound = $true
        $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        
        if ($process) {
            Write-Host "Stopping process on port ${port}: $($process.Name) (PID $($process.Id))" -ForegroundColor Yellow
            
            try {
                Stop-Process -Id $process.Id -Force
                Write-Host "  Stopped PID $($process.Id)" -ForegroundColor Green
            } catch {
                Write-Host "  Failed to stop PID $($process.Id): $_" -ForegroundColor Red
            }
        }
    }
}

# Also look for Python processes that might be services
Write-Host ""
Write-Host "Checking for Python/Uvicorn processes..." -ForegroundColor Yellow

$pythonProcesses = Get-Process | Where-Object { 
    $_.ProcessName -like "*python*" -or $_.ProcessName -like "*uvicorn*" 
}

if ($pythonProcesses) {
    Write-Host "Found $($pythonProcesses.Count) Python/Uvicorn processes:" -ForegroundColor Yellow
    
    foreach ($proc in $pythonProcesses) {
        Write-Host "  PID $($proc.Id): $($proc.Name) (Started: $($proc.StartTime))" -ForegroundColor Gray
    }
    
    Write-Host ""
    $response = Read-Host "Do you want to stop all Python processes? (yes/no)"
    
    if ($response -eq "yes") {
        foreach ($proc in $pythonProcesses) {
            try {
                Stop-Process -Id $proc.Id -Force
                Write-Host "  Stopped PID $($proc.Id)" -ForegroundColor Green
            } catch {
                Write-Host "  Failed to stop PID $($proc.Id): $_" -ForegroundColor Red
            }
        }
    }
}

if (-not $processesFound -and -not $pythonProcesses) {
    Write-Host "No service processes found running." -ForegroundColor Green
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Cleanup Complete" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start services properly, use: .\start_guardian.ps1" -ForegroundColor Cyan
