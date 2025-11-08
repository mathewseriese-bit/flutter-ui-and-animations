# Guardian System Architecture Diagram

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         OPERATOR                             │
│                                                               │
│  Commands:                                                    │
│  • .\start_guardian.ps1    → Start everything                │
│  • Ctrl+C                  → Stop everything                 │
│  • .\services_start\stop_all_services.ps1 → Emergency stop  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM GUARDIAN                           │
│                  (Single Source of Truth)                    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ServiceManager                                        │   │
│  │ • Track service PIDs                                  │   │
│  │ • Check port availability                             │   │
│  │ • Start/stop services                                 │   │
│  │ • Prevent duplicate launches                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ HealthMonitor                                         │   │
│  │ • HTTP health checks (30s interval)                   │   │
│  │ • Exponential backoff (5s → 300s)                     │   │
│  │ • Auto-restart on failure                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Background Monitor                                    │   │
│  │ • Continuous service monitoring                       │   │
│  │ • Log service status                                  │   │
│  │ • Coordinate restarts                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Outputs: guardian.log                                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ Manages
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND SERVICES                         │
│                                                               │
│  ┌───────────────────┐  ┌───────────────────┐               │
│  │ Character Extract │  │ Document Processor│               │
│  │ Port: 8001        │  │ Port: 8002        │               │
│  │ /health           │  │ /health           │               │
│  └───────────────────┘  └───────────────────┘               │
│                                                               │
│  ┌───────────────────┐  ┌───────────────────┐               │
│  │ Query Engine      │  │ Metadata Service  │               │
│  │ Port: 8003        │  │ Port: 8004        │               │
│  │ /health           │  │ /health           │               │
│  └───────────────────┘  └───────────────────┘               │
│                                                               │
│  ┌───────────────────┐  ┌───────────────────┐               │
│  │ RAG Service       │  │ Voice Synthesis   │               │
│  │ Port: 8005        │  │ Port: 8006        │               │
│  │ /health           │  │ /health           │               │
│  └───────────────────┘  └───────────────────┘               │
│                                                               │
│  Each service:                                                │
│  • FastAPI application                                        │
│  • Uvicorn ASGI server                                        │
│  • Health check endpoint                                      │
│  • Independent process                                        │
└─────────────────────────────────────────────────────────────┘
```

## Service Startup Sequence

```
Guardian Starts
    │
    ├──> 1. Character Extraction (8001)
    │       │
    │       └──> Wait 2s for port bind
    │            └──> Wait 3s before next
    │
    ├──> 2. Document Processor (8002)
    │       │
    │       └──> Wait 2s for port bind
    │            └──> Wait 3s before next
    │
    ├──> 3. Query Engine (8003)
    │       │
    │       └──> Wait 2s for port bind
    │            └──> Wait 3s before next
    │
    ├──> 4. Metadata Service (8004)
    │       │
    │       └──> Wait 2s for port bind
    │            └──> Wait 3s before next
    │
    ├──> 5. RAG Service (8005)
    │       │
    │       └──> Wait 2s for port bind
    │            └──> Wait 3s before next
    │
    └──> 6. Voice Synthesis (8006)
            │
            └──> Wait 2s for port bind
                 └──> All services started
                      └──> Begin monitoring loop
```

## Health Monitoring Loop

```
┌─────────────────────────────────────────┐
│ Every 30 seconds                        │
│                                         │
│  For each service:                      │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 1. Check if PID exists          │   │
│  │    ├─ Yes → Continue to health  │   │
│  │    └─ No  → Restart with backoff│   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 2. HTTP GET /health             │   │
│  │    ├─ 200 + "healthy" → OK      │   │
│  │    └─ Fail → Restart with backoff│  │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 3. Log status                   │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

## Restart Flow with Backoff

```
Service Fails
    │
    ├──> Apply backoff delay (5s first time)
    │
    ├──> Stop existing process
    │       └──> Terminate (10s timeout)
    │            └──> Kill if needed (5s timeout)
    │
    ├──> Start new process
    │       └──> Wait 2s for port bind
    │
    ├──> Increase backoff for next failure
    │       └──> 5s → 10s → 20s → 40s ... → 300s max
    │
    └──> Update restart counter
```

## Port Conflict Prevention

```
Start Service Request
    │
    ├──> Check if port is in use
    │       │
    │       ├──> Yes:
    │       │    ├──> Get PID using port
    │       │    ├──> Track as external process
    │       │    └──> Skip start (log warning)
    │       │
    │       └──> No:
    │            ├──> Start service process
    │            ├──> Track PID
    │            └──> Mark as Guardian-managed
    │
    └──> Continue with next service
```

## Shutdown Flow

```
Ctrl+C Pressed
    │
    ├──> Catch KeyboardInterrupt
    │
    ├──> Cancel monitoring task
    │
    ├──> For each service (reverse order):
    │       │
    │       ├──> Send TERMINATE signal
    │       │
    │       ├──> Wait 10 seconds for graceful exit
    │       │
    │       └──> If still running:
    │            └──> Send KILL signal
    │                 └──> Wait 5 seconds
    │
    └──> Guardian exits
         └──> All services stopped
```

## File Structure

```
Auralis_App/
│
├── start_guardian.ps1          ← YOU START HERE
│   └──> Launches guardian.py
│
├── backend/services/
│   └── system_guardian/
│       └── guardian.py         ← CORE LOGIC
│           ├── ServiceManager
│           ├── HealthMonitor
│           ├── STARTUP_ORDER
│           └── main()
│
├── services_start/
│   ├── start_all_services.ps1  ← DEPRECATED
│   └── stop_all_services.ps1   ← EMERGENCY USE
│
└── docs/services/
    └── guardian_startup_flow.md ← FULL DOCUMENTATION
```

## Common Scenarios

### Scenario 1: Normal Operation
```
start_guardian.ps1
    → Guardian starts
    → All 5 services start
    → Monitoring begins
    → Services stay healthy
    → (Run until operator stops)
```

### Scenario 2: Service Crashes
```
Service crashes
    → Next health check (≤30s)
    → Guardian detects failure
    → Applies backoff (5s)
    → Restarts service
    → Service recovers
    → Monitoring continues
```

### Scenario 3: Port Already in Use
```
start_guardian.ps1
    → Guardian checks port 8001
    → Port is in use (PID 1234)
    → Guardian logs warning
    → Guardian tracks PID 1234
    → Skips starting on 8001
    → Continues with other ports
```

### Scenario 4: Clean Shutdown
```
Ctrl+C in Guardian window
    → Guardian catches signal
    → Stops monitoring
    → Stops all services (reverse order)
    → Waits for clean exit
    → Guardian exits
    → All processes terminated
```

## Key Design Principles

1. **Single Source of Truth**
   - Guardian is the only orchestrator
   - All service state tracked centrally
   - No conflicting launchers

2. **Defensive Programming**
   - Check ports before starting
   - Track external processes
   - Exponential backoff
   - Graceful degradation

3. **Operator Friendly**
   - Single command to start
   - Single command to stop
   - Clear logs
   - Comprehensive documentation

4. **Production Ready**
   - Health monitoring
   - Auto-recovery
   - Clean shutdown
   - No orphaned processes

## Legend

```
┌──┐
│  │  Component boundary
└──┘

 │    Flow direction
 ▼

 →    Direct action

 ├──  Branch/decision point
 └──
```
