# Guardian Service Orchestration System

## Overview

This repository now includes a complete **Guardian Service Orchestration System** for the Auralis backend services. This system was created to address duplicate service launches, operator confusion, and provide a single, dependable startup story.

## Problem Solved

**Before Guardian:**
- Multiple scripts (`start_all_services.ps1`, `start_guardian.ps1`) caused confusion
- Services could be launched multiple times (port conflicts)
- No health monitoring or auto-recovery
- Operators didn't know which script to use
- Difficult to stop all services cleanly

**After Guardian:**
- Single entry point: `start_guardian.ps1`
- No duplicate launches (port conflict detection)
- Automatic health monitoring and recovery
- Clear operator workflow
- Clean shutdown mechanism

## Quick Start

```powershell
# Navigate to Auralis_App
cd Auralis_App

# First time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start all services
.\start_guardian.ps1

# Stop all services (Ctrl+C in Guardian window)
# OR
.\services_start\stop_all_services.ps1
```

## What's Included

### Core Components

1. **System Guardian** (`Auralis_App/backend/services/system_guardian/`)
   - Orchestrates all service lifecycle
   - Monitors health every 30 seconds
   - Auto-restarts failed services with exponential backoff
   - Prevents duplicate launches via port checking

2. **Five Backend Services** (Ports 8001-8005)
   - Character Extraction Service
   - Document Processor Service
   - Query Engine Service
   - Metadata Service
   - RAG Service
   - Each with `/health` endpoint

3. **PowerShell Scripts**
   - `start_guardian.ps1` - Recommended startup method
   - `services_start/start_all_services.ps1` - Deprecated (with warnings)
   - `services_start/stop_all_services.ps1` - Emergency cleanup

### Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Quick Reference | [`Auralis_App/QUICK_REFERENCE.md`](Auralis_App/QUICK_REFERENCE.md) | Operator cheat sheet |
| README | [`Auralis_App/README.md`](Auralis_App/README.md) | Getting started guide |
| Implementation Summary | [`Auralis_App/IMPLEMENTATION_SUMMARY.md`](Auralis_App/IMPLEMENTATION_SUMMARY.md) | Validation results |
| Guardian Startup Flow | [`docs/services/guardian_startup_flow.md`](docs/services/guardian_startup_flow.md) | Comprehensive 21KB deep-dive |
| Architecture Diagrams | [`docs/services/guardian_architecture.md`](docs/services/guardian_architecture.md) | Visual system overview |

### Validation

Run the validation script to verify system integrity:

```powershell
cd Auralis_App
python validate_guardian.py
```

**Expected output:** All 5 checks pass
- ✓ Guardian module imports
- ✓ Service configuration valid
- ✓ All service files exist
- ✓ Port checking works
- ✓ All dependencies available

## Architecture Highlights

### Single Source of Truth
The Guardian is the **only recommended** way to start services. It:
- Checks if ports are already in use before starting
- Tracks all service PIDs
- Monitors health continuously
- Auto-restarts failures
- Provides clean shutdown

### Health Monitoring
- HTTP health checks every 30 seconds
- Services must return `{"status": "healthy"}`
- Failed services restart with exponential backoff (5s → 300s)
- Restart counts tracked per service

### Port Conflict Prevention
```python
# Before starting a service:
1. Check if port is in use
2. If yes: track external PID, skip start
3. If no: start service, track Guardian PID
```

### Graceful Shutdown
```
Ctrl+C → Stop monitoring → Stop services (reverse order) → Exit
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Character Extraction | 8001 | Extracts characters from text |
| Document Processor | 8002 | Processes documents |
| Query Engine | 8003 | Executes queries |
| Metadata Service | 8004 | Manages metadata |
| RAG Service | 8005 | Retrieval-Augmented Generation |

## Common Operations

### Check What's Running
```powershell
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005 }
```

### Check Service Health
```powershell
Invoke-WebRequest -Uri http://localhost:8001/health | ConvertFrom-Json
```

### View Guardian Logs
```powershell
Get-Content Auralis_App/guardian.log -Tail 50
```

### Emergency Stop
```powershell
cd Auralis_App
.\services_start\stop_all_services.ps1
```

## Troubleshooting

### Port Conflicts
```powershell
# Stop everything
.\services_start\stop_all_services.ps1

# Restart
.\start_guardian.ps1
```

### Service Won't Start
Check `guardian.log` for errors:
```powershell
Get-Content Auralis_App/guardian.log -Tail 50
```

### Guardian Already Running
```powershell
# Check if running
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 9000 }

# Stop and restart
.\services_start\stop_all_services.ps1
.\start_guardian.ps1
```

## Technical Details

### Technologies Used
- **Python 3.8+**: Core language
- **FastAPI**: Service framework
- **Uvicorn**: ASGI server
- **psutil**: Process/port monitoring
- **aiohttp**: HTTP client for health checks
- **asyncio**: Asynchronous operations

### Key Files
```
Auralis_App/
├── start_guardian.ps1                 # Main entry point
├── validate_guardian.py               # Validation script
├── requirements.txt                   # Python dependencies
├── backend/services/
│   ├── system_guardian/guardian.py    # Core orchestration (400+ lines)
│   ├── character_extraction/service.py
│   ├── document_processor/service.py
│   ├── query_engine/service.py
│   ├── metadata_service/service.py
│   └── rag_service/service.py
└── services_start/
    ├── start_all_services.ps1         # Deprecated
    └── stop_all_services.ps1          # Emergency use
```

## Success Criteria Met

✅ Single blessed startup path  
✅ No duplicate service launches  
✅ Automatic health monitoring  
✅ Auto-recovery from failures  
✅ Clear operator workflows  
✅ Comprehensive documentation  
✅ Validation and testing tools  
✅ Clean shutdown mechanism  

## For Developers

### Adding a New Service

1. Create service directory and file:
   ```powershell
   mkdir Auralis_App\backend\services\my_service
   # Create service.py with FastAPI app
   ```

2. Add to `STARTUP_ORDER` in `guardian.py`:
   ```python
   {
       'name': 'my_service',
       'port': 8006,
       'path': 'backend/services/my_service/service.py',
       'health_endpoint': '/health'
   }
   ```

3. Test with Guardian:
   ```powershell
   .\start_guardian.ps1
   ```

### Service Requirements

Each service must:
- Be a FastAPI application
- Have a `/health` endpoint
- Return `{"status": "healthy", "service": "name", "port": 8xxx}`
- Run on a unique port

## Resources

- **Quick Reference**: See [`Auralis_App/QUICK_REFERENCE.md`](Auralis_App/QUICK_REFERENCE.md)
- **Detailed Guide**: See [`docs/services/guardian_startup_flow.md`](docs/services/guardian_startup_flow.md)
- **Architecture**: See [`docs/services/guardian_architecture.md`](docs/services/guardian_architecture.md)
- **Implementation**: See [`Auralis_App/IMPLEMENTATION_SUMMARY.md`](Auralis_App/IMPLEMENTATION_SUMMARY.md)

## Support

For issues:
1. Check `guardian.log`
2. Run `python validate_guardian.py`
3. Review documentation
4. Verify ports are available

---

**Status**: ✅ Complete and Production Ready  
**Version**: 1.0  
**Date**: 2025-10-30

## License

Same as the main repository.
