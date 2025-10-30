# Guardian & Service Orchestration Analysis

## Executive Summary

This document provides a comprehensive analysis of the Auralis service orchestration system, identifying the root causes of duplicate service launches and operator confusion. It proposes a unified solution centered on the **System Guardian** as the single source of truth for service management.

## Problem Statement

### Key Pain Points Identified

1. **Duplicate Service Launches**: Multiple entry points (manual scripts and Guardian) can start services independently, leading to port conflicts and resource waste
2. **Operator Confusion**: Unclear which script to use (`start_all_services.ps1` vs `start_guardian.ps1`)
3. **Process Management**: Difficulty tracking which services are running and who started them
4. **No Coordination**: Manual launcher and Guardian don't communicate, causing conflicts
5. **Recovery Issues**: Guardian may attempt to restart services that were manually started

### Evidence

- Multiple Python processes starting simultaneously
- Port conflicts (some services fail to bind)
- Hanging processes that persist after attempts to stop services
- Guardian attempting to restart services that are already running

## Architecture Overview

### Service Entry Points

#### 1. Manual Launcher: `services_start/start_all_services.ps1`

**Purpose**: Originally designed for quick manual service startup  
**Behavior**:
- Spawns each service in a new PowerShell window
- No coordination with Guardian
- No health monitoring
- No tracking of service state

**Problems**:
- Creates orphaned processes
- Doesn't check if services are already running elsewhere
- No automatic recovery
- Conflicts with Guardian if both are used

#### 2. System Guardian: `start_guardian.ps1` → `backend/services/system_guardian/guardian.py`

**Purpose**: Centralized service orchestration and monitoring  
**Behavior**:
- Starts services in defined order (STARTUP_ORDER)
- Monitors service health via HTTP endpoints
- Auto-restarts failed services with exponential backoff
- Tracks service PIDs and ports
- Provides single shutdown point

**Advantages**:
- Single source of truth
- Prevents duplicate launches (port checking)
- Health monitoring
- Automatic recovery
- Clean shutdown

### Service Configuration

Services are defined in `guardian.py` with the following structure:

```python
STARTUP_ORDER = [
    {
        'name': 'character_extraction',
        'port': 8001,
        'path': 'backend/services/character_extraction/service.py',
        'health_endpoint': '/health'
    },
    # ... more services
]
```

**Service Ports**:
- 8001: Character Extraction
- 8002: Document Processor  
- 8003: Query Engine
- 8004: Metadata Service
- 8005: RAG Service
- 9000: Guardian (future API endpoint)

### Service Architecture

Each service is a FastAPI application with:
- Health check endpoint (`/health`)
- Service-specific endpoints
- Uvicorn ASGI server
- Runs in isolated process

## Root Cause Analysis

### 1. Duplicate Launch Mechanism

**How it Happens**:
```
Operator runs: start_all_services.ps1
  └─> Spawns 5 PowerShell windows
      └─> Each starts a Python process
          └─> Services bind to ports 8001-8005

Operator runs: start_guardian.ps1
  └─> Guardian checks ports
      └─> Sees ports 8001-8005 in use
          └─> Logs warning but continues
              └─> May attempt restart on health failure
```

**Result**: 
- Port conflict warnings
- Duplicate processes attempting to bind same ports
- Guardian tracking external PIDs it didn't start
- Confusion about service ownership

### 2. Process Lifecycle Issues

**Manual Launcher**:
- Spawns processes with `Start-Process -WindowStyle Normal`
- No parent-child relationship tracking
- Processes persist even if launcher exits
- No cleanup mechanism

**Guardian**:
- Uses `subprocess.Popen` with proper tracking
- Maintains PID registry
- Clean shutdown via `terminate()` or `kill()`

### 3. Health Check Conflicts

**Scenario**:
```
1. Service started manually (no health monitoring)
2. Guardian starts and sees port in use
3. Guardian tracks external PID
4. Service has a transient issue
5. Guardian health check fails
6. Guardian attempts restart
7. Stops process (may be wrong one)
8. Starts new process
9. Port conflict if original didn't fully stop
```

### 4. Operator Workflow Confusion

**Current State**:
- Two scripts with similar names
- No clear guidance on which to use
- Manual script doesn't warn about Guardian
- Guardian doesn't check for manually started services initially

## Orchestration Flow Analysis

### Current Guardian Flow

```
1. Guardian Startup
   ├─> Initialize ServiceManager
   ├─> Find virtual environment Python
   └─> Initialize HealthMonitor

2. Start All Services
   ├─> For each service in STARTUP_ORDER:
   │   ├─> Check if port in use
   │   │   ├─> Yes: Track external PID, skip start
   │   │   └─> No: Start service
   │   ├─> Wait 2 seconds for port binding
   │   └─> Wait 3 seconds before next service

3. Background Monitoring Loop (every 30s)
   ├─> For each service:
   │   ├─> Check if process running (PID exists)
   │   │   └─> No: Restart with backoff
   │   ├─> Check health endpoint
   │   │   └─> Unhealthy: Restart with backoff
   │   └─> Log status

4. Restart Logic
   ├─> Apply exponential backoff delay
   ├─> Stop existing process
   ├─> Start new process
   ├─> Increase backoff for next failure
   └─> Update restart counter
```

### Manual Launcher Flow

```
1. Manual Launcher Startup
   ├─> Find virtual environment Python
   ├─> For each service:
   │   ├─> Check if port in use
   │   │   ├─> Yes: Skip with warning
   │   │   └─> No: Start in new window
   │   └─> Wait 2 seconds
   └─> Exit (processes remain running)

2. No monitoring or tracking
3. No automatic recovery
4. No centralized shutdown
```

## Proposed Solution

### Single Blessed Path: Use Guardian Only

#### Phase 1: Deprecate Manual Launcher (Implemented)

✅ **Changes Made**:
1. Added deprecation warning to `start_all_services.ps1`
2. Script now requires explicit confirmation to continue
3. Warns users to use `start_guardian.ps1` instead
4. Explains benefits of Guardian approach

#### Phase 2: Guardian Improvements (Implemented)

✅ **Features Added**:
1. **Port Conflict Detection**: Guardian checks ports before starting
2. **External Process Tracking**: Recognizes manually started services
3. **Exponential Backoff**: Prevents restart storms (5s → 300s)
4. **Health Monitoring**: Checks `/health` endpoint every 30s
5. **Clean Shutdown**: Graceful termination with fallback to force kill
6. **Logging**: Comprehensive logging to `guardian.log` and console

#### Phase 3: Operational Best Practices

**Single Command Startup**:
```powershell
.\start_guardian.ps1
```

**Single Command Shutdown**:
```powershell
# Press Ctrl+C in Guardian window
# OR
.\services_start\stop_all_services.ps1
```

**Check Service Status**:
```powershell
# Check what's using service ports
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001,8002,8003,8004,8005,9000 } |
  ForEach-Object { 
    $proc = Get-Process -Id $_.OwningProcess
    [PSCustomObject]@{
      Port = $_.LocalPort
      PID = $_.OwningProcess
      Name = $proc.Name
      StartTime = $proc.StartTime
    }
  }
```

### Updated Operator Workflow

#### Starting Services

```powershell
# 1. Ensure clean state
.\services_start\stop_all_services.ps1

# 2. Start Guardian (starts all services)
.\start_guardian.ps1

# Guardian will:
# - Check for existing services on ports
# - Start services in correct order
# - Begin health monitoring
# - Auto-restart failures
```

#### Stopping Services

```powershell
# Option 1: Press Ctrl+C in Guardian window
# - Guardian will gracefully stop all services

# Option 2: Run stop script
.\services_start\stop_all_services.ps1
# - Stops all processes on service ports
# - Optionally stops all Python processes
```

#### Troubleshooting

**Problem**: Services won't start (port conflicts)

```powershell
# 1. Check what's using ports
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005 }

# 2. Force stop everything
.\services_start\stop_all_services.ps1

# 3. Restart Guardian
.\start_guardian.ps1
```

**Problem**: Service keeps restarting

```
# Check Guardian logs
Get-Content guardian.log -Tail 50

# Common causes:
# - Service failing health checks
# - Port binding issues
# - Dependency problems
# - Resource exhaustion
```

**Problem**: Guardian won't start (already running)

```powershell
# 1. Check if Guardian is running
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 9000 }

# 2. Stop existing Guardian
.\services_start\stop_all_services.ps1

# 3. Start fresh
.\start_guardian.ps1
```

## Technical Implementation Details

### Guardian Components

#### ServiceManager Class

**Responsibilities**:
- Locate virtual environment Python
- Check port availability
- Start/stop service processes
- Track service PIDs and metadata
- Report service status

**Key Methods**:
- `is_port_in_use(port)`: Checks if port is bound
- `is_service_running(name)`: Checks if tracked service is alive
- `start_service(config)`: Starts service if not running
- `stop_service(name)`: Gracefully stops service
- `get_service_status()`: Returns status dict for all services

#### HealthMonitor Class

**Responsibilities**:
- Perform HTTP health checks
- Manage restart backoff timers
- Coordinate service restarts
- Track health status history

**Key Methods**:
- `check_health(config)`: HTTP GET to `/health` endpoint
- `get_backoff_delay(name)`: Returns current backoff time
- `increase_backoff(name)`: Exponential backoff increase
- `restart_service(config)`: Restart with backoff applied

#### Background Monitor

**Async Loop** (30-second cycle):
```python
while True:
    for service in STARTUP_ORDER:
        if not service_manager.is_service_running(service):
            health_monitor.restart_service(service)
        elif not health_monitor.check_health(service):
            health_monitor.restart_service(service)
    
    await asyncio.sleep(30)
```

### Service Health Endpoint Contract

Each service must implement:

```python
@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",  # Required: "healthy" or "unhealthy"
        "service": "service_name",  # Required
        "port": 8001,  # Required
        # Optional additional fields
    })
```

**Guardian Expectations**:
- HTTP 200 status code
- JSON response
- `status` field with value `"healthy"`

## Validation & Testing

### Validation Scenarios

#### Scenario 1: Normal Startup

```powershell
# Clean start
.\start_guardian.ps1
```

**Expected**:
- All 5 services start in order
- No errors or warnings
- All health checks pass
- Guardian remains running

**Validation**:
```powershell
# Check all services are running
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005 } | 
  Measure-Object | Select-Object -ExpandProperty Count
# Should return: 5
```

#### Scenario 2: Service Failure Recovery

```powershell
# 1. Start Guardian
.\start_guardian.ps1

# 2. In another window, kill a service
$proc = Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 8003 } | 
  Select-Object -First 1
Stop-Process -Id $proc.OwningProcess -Force
```

**Expected**:
- Guardian detects service down (within 30s)
- Guardian waits backoff delay (5s first time)
- Guardian restarts service
- Service comes back healthy

**Validation**:
- Check `guardian.log` for restart messages
- Verify service is running again

#### Scenario 3: Port Conflict Detection

```powershell
# 1. Start a service manually (simulate conflict)
& .\.venv\Scripts\python.exe `
  .\backend\services\character_extraction\service.py

# 2. Start Guardian
.\start_guardian.ps1
```

**Expected**:
- Guardian detects port 8001 in use
- Guardian logs warning
- Guardian tracks external PID
- Guardian starts remaining services normally
- No duplicate launch attempts

#### Scenario 4: Graceful Shutdown

```powershell
# 1. Start Guardian
.\start_guardian.ps1

# 2. Press Ctrl+C
```

**Expected**:
- Guardian catches shutdown signal
- Guardian stops all services in reverse order
- All processes terminate within 10 seconds
- No orphaned processes

**Validation**:
```powershell
# Check no services remain
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005 }
# Should return: nothing
```

## Migration Guide

### For Operators Currently Using Manual Launcher

**Day 1**: Awareness
- Read this document
- Understand Guardian benefits
- Plan migration timing

**Day 2**: Testing
- Stop all current services: `.\services_start\stop_all_services.ps1`
- Test Guardian: `.\start_guardian.ps1`
- Verify all services start
- Test Ctrl+C shutdown
- Review logs: `guardian.log`

**Day 3**: Switch Over
- Update documentation to reference Guardian
- Update runbooks to use Guardian
- Update VS Code tasks if applicable
- Deprecate manual launcher usage

**Ongoing**: Monitor
- Check `guardian.log` regularly
- Monitor service restart counts
- Report issues with health checks

### For Developers Adding New Services

1. Create service in `backend/services/<service_name>/`
2. Implement `/health` endpoint
3. Add to `STARTUP_ORDER` in `guardian.py`
4. Test with Guardian
5. Document any dependencies

## Diagrams

### Current State (Before Fix)

```
┌─────────────────────────────────────────────────────────┐
│ Operator                                                 │
└────┬─────────────────────────────────┬──────────────────┘
     │                                  │
     │ (1) Manual Launch                │ (2) Guardian Launch
     │                                  │
     ▼                                  ▼
┌─────────────────┐              ┌────────────────────┐
│ start_all.ps1   │              │ start_guardian.ps1 │
└────┬────────────┘              └────┬───────────────┘
     │                                │
     │ Spawns windows                 │ Starts Guardian
     │                                │
     ▼                                ▼
┌─────────────────┐              ┌────────────────────┐
│ Service A (8001)│              │ Guardian           │
│ Service B (8002)│              │  ├─ Check ports    │
│ Service C (8003)│              │  ├─ Start services │
│ Service D (8004)│              │  ├─ Monitor health │
│ Service E (8005)│              │  └─ Auto-restart   │
└─────────────────┘              └────┬───────────────┘
                                      │
     ┌────────────────────────────────┘
     │
     ▼
┌─────────────────┐
│ Service A (8001)│ ◄─── CONFLICT!
│ Service B (8002)│
│ Service C (8003)│
│ Service D (8004)│
│ Service E (8005)│
└─────────────────┘
```

### Desired State (After Fix)

```
┌─────────────────────────────────────────────────────────┐
│ Operator                                                 │
└────┬────────────────────────────────────────────────────┘
     │
     │ Single entry point
     │
     ▼
┌────────────────────┐
│ start_guardian.ps1 │
└────┬───────────────┘
     │
     │ Starts Guardian
     │
     ▼
┌────────────────────────────────────────────────────┐
│ System Guardian (Single Source of Truth)           │
│                                                     │
│  1. Check existing services (port scan)            │
│  2. Start services in order                        │
│  3. Monitor health (30s loop)                      │
│  4. Auto-restart failures (with backoff)           │
│  5. Track all PIDs                                 │
│  6. Clean shutdown on Ctrl+C                       │
│                                                     │
└────┬───────────────────────────────────────────────┘
     │
     │ Manages lifecycle
     │
     ▼
┌─────────────────────────────────────────────────┐
│ Services (Single Instance Each)                 │
│                                                  │
│  ├─ Character Extraction (8001)                 │
│  ├─ Document Processor (8002)                   │
│  ├─ Query Engine (8003)                         │
│  ├─ Metadata Service (8004)                     │
│  └─ RAG Service (8005)                          │
│                                                  │
│  Each has /health endpoint                      │
└──────────────────────────────────────────────────┘
```

### Guardian State Machine

```
                   ┌──────────────┐
                   │   Stopped    │
                   └──────┬───────┘
                          │
                          │ start_guardian.ps1
                          ▼
                   ┌──────────────┐
                   │  Initializing│
                   │              │
                   │ - Find venv  │
                   │ - Check ports│
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   Starting   │
                   │   Services   │
                   │              │
                   │ - For each:  │
                   │   - Port chk │
                   │   - Start    │
                   │   - Wait     │
                   └──────┬───────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │        Running (Monitoring)      │
        │                                  │
        │  Every 30s:                      │
        │  ┌─────────────────────────┐    │
        │  │ For each service:       │    │
        │  │  1. Check PID alive?    │    │
        │  │     No → Restart        │    │
        │  │  2. Check /health?      │    │
        │  │     Unhealthy → Restart │    │
        │  │  3. Log status          │    │
        │  └─────────────────────────┘    │
        │                                  │
        └────────┬─────────────────────────┘
                 │
                 │ Ctrl+C
                 ▼
          ┌──────────────┐
          │  Shutting    │
          │    Down      │
          │              │
          │ - Stop svcs  │
          │ - Wait/kill  │
          │ - Exit       │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │   Stopped    │
          └──────────────┘
```

## Summary & Recommendations

### Key Findings

1. **Root Cause**: Multiple independent entry points with no coordination
2. **Impact**: Duplicate launches, port conflicts, operator confusion
3. **Solution**: Single orchestrator (Guardian) as source of truth

### Implemented Changes

✅ **Guardian System**:
- Comprehensive service lifecycle management
- Health monitoring with exponential backoff
- Port conflict detection
- External process tracking
- Clean shutdown handling

✅ **Manual Launcher Deprecation**:
- Warning message added
- Requires confirmation to proceed
- Guides users to Guardian

✅ **Stop Script Enhancement**:
- Stops services on all known ports
- Identifies Python processes
- Asks for confirmation before killing

✅ **Documentation**:
- Complete orchestration flow analysis
- Operator workflows
- Troubleshooting guides
- Migration instructions

### Recommendations

**Immediate (Week 1)**:
1. ✅ Deploy Guardian system
2. ✅ Update operator documentation
3. ✅ Deprecate manual launcher
4. ✅ Train operators on Guardian workflow

**Short Term (Month 1)**:
5. Monitor Guardian logs for issues
6. Collect operator feedback
7. Add Guardian API endpoint (port 9000) for status queries
8. Create Grafana dashboard for service health

**Long Term (Quarter 1)**:
9. Add Guardian web UI for non-PowerShell users
10. Implement service dependency management
11. Add resource usage monitoring
12. Create automated health checks in CI/CD

### Success Metrics

- ✅ Zero duplicate service launches
- ✅ Single command to start all services
- ✅ Single command to stop all services
- ✅ Automatic recovery from failures
- ✅ Clear operator understanding of system state

## Appendix

### File Locations

```
Auralis_App/
├── start_guardian.ps1              # Main entry point
├── services_start/
│   ├── start_all_services.ps1      # Deprecated manual launcher
│   └── stop_all_services.ps1       # Cleanup script
├── backend/
│   └── services/
│       ├── system_guardian/
│       │   ├── __init__.py
│       │   └── guardian.py         # Core orchestration logic
│       ├── character_extraction/
│       │   └── service.py
│       ├── document_processor/
│       │   └── service.py
│       ├── query_engine/
│       │   └── service.py
│       ├── metadata_service/
│       │   └── service.py
│       └── rag_service/
│           └── service.py
└── docs/
    └── services/
        └── guardian_startup_flow.md # This document
```

### Requirements

Python packages needed (add to `requirements.txt`):

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
psutil>=5.9.0
aiohttp>=3.9.0
```

### Environment Setup

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install fastapi uvicorn psutil aiohttp

# 4. Start Guardian
.\start_guardian.ps1
```

### Common Commands Reference

```powershell
# Start everything
.\start_guardian.ps1

# Stop everything  
.\services_start\stop_all_services.ps1

# Check what's running
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005,9000 }

# View Guardian logs
Get-Content guardian.log -Tail 50 -Wait

# Check Python processes
Get-Process | Where-Object { $_.ProcessName -like "*python*" }

# Kill specific port
$conn = Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 8001 }
Stop-Process -Id $conn.OwningProcess -Force
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-30  
**Author**: System Guardian Implementation Team  
**Status**: Complete - Implementation Ready
