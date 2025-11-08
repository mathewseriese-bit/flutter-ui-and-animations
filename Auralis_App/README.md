# Auralis Application - Backend Services

## Overview

The Auralis backend consists of multiple microservices orchestrated by the **System Guardian**. The Guardian provides centralized service lifecycle management, health monitoring, and automatic recovery.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows PowerShell (or PowerShell Core on other platforms)

### Initial Setup

```powershell
# 1. Navigate to Auralis_App directory
cd Auralis_App

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate     # Linux/Mac

# 4. Install dependencies
pip install -r requirements.txt
```

### Starting Services

**Recommended Method** (Single Command):

```powershell
.\start_guardian.ps1
```

This will:
- Start all services in the correct order
- Monitor service health
- Automatically restart failed services
- Provide a single window for all logs

### Stopping Services

**Option 1**: Press `Ctrl+C` in the Guardian window

**Option 2**: Run the stop script

```powershell
.\services_start\stop_all_services.ps1
```

## Services

The following services are managed by the Guardian:

| Service | Port | Description |
|---------|------|-------------|
| Character Extraction | 8001 | Extracts characters from text |
| Document Processor | 8002 | Processes documents |
| Query Engine | 8003 | Executes queries |
| Metadata Service | 8004 | Manages metadata |
| RAG Service | 8005 | Retrieval-Augmented Generation |
| Voice Synthesis | 8006 | Text-to-speech synthesis |
| Guardian | 9000 | Service orchestrator (future API) |

## Service Health

Each service exposes a `/health` endpoint that returns:

```json
{
  "status": "healthy",
  "service": "service_name",
  "port": 8001
}
```

Check service health:

```powershell
# Using curl or Invoke-WebRequest
Invoke-WebRequest -Uri http://localhost:8001/health | ConvertFrom-Json
```

## Troubleshooting

### Services Won't Start (Port Conflicts)

```powershell
# 1. Check what's using the ports
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8006 }

# 2. Stop everything
.\services_start\stop_all_services.ps1

# 3. Restart Guardian
.\start_guardian.ps1
```

### Service Keeps Restarting

Check Guardian logs:

```powershell
Get-Content guardian.log -Tail 50
```

Common causes:
- Service failing health checks
- Port binding issues
- Dependency problems
- Resource exhaustion

### Guardian Already Running

```powershell
# Check if Guardian is running on port 9000
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 9000 }

# Stop existing Guardian
.\services_start\stop_all_services.ps1

# Start fresh
.\start_guardian.ps1
```

## Architecture

### Guardian System

The System Guardian (`backend/services/system_guardian/guardian.py`) provides:

1. **Service Lifecycle Management**
   - Starts services in dependency order
   - Tracks process IDs and ports
   - Graceful shutdown

2. **Health Monitoring**
   - HTTP health checks every 30 seconds
   - Automatic restart on failure
   - Exponential backoff (5s → 300s)

3. **Conflict Prevention**
   - Port availability checking
   - External process tracking
   - No duplicate launches

### Service Structure

Each service follows this structure:

```
backend/services/<service_name>/
├── __init__.py
└── service.py          # FastAPI application
```

## Development

### Adding a New Service

1. Create service directory:
   ```powershell
   mkdir backend\services\my_service
   ```

2. Create `service.py` with FastAPI app:
   ```python
   from fastapi import FastAPI
   import uvicorn
   
   app = FastAPI(title="My Service")
   
   @app.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "service": "my_service",
           "port": 8006
       }
   
   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8006)
   ```

3. Add to Guardian's `STARTUP_ORDER` in `guardian.py`:
   ```python
   {
       'name': 'my_service',
       'port': 8006,
       'path': 'backend/services/my_service/service.py',
       'health_endpoint': '/health'
   }
   ```

4. Test with Guardian:
   ```powershell
   .\start_guardian.ps1
   ```

### Testing Services

```powershell
# Start Guardian
.\start_guardian.ps1

# In another window, test endpoints
Invoke-WebRequest -Uri http://localhost:8001/health
Invoke-WebRequest -Uri http://localhost:8002/health
# etc...
```

## Documentation

For detailed information about the Guardian system and orchestration flow, see:

**[Guardian Startup Flow Documentation](../docs/services/guardian_startup_flow.md)**

This document includes:
- Architecture overview
- Root cause analysis of duplicate launches
- Operator workflows
- Troubleshooting guides
- Migration instructions

## Deprecated Scripts

⚠️ **Do NOT use these scripts** (kept for reference only):

- `services_start/start_all_services.ps1` - Manual launcher (causes conflicts)

Always use `start_guardian.ps1` instead.

## Support

For issues or questions:
1. Check the [Guardian Startup Flow Documentation](../docs/services/guardian_startup_flow.md)
2. Review `guardian.log` for error messages
3. Verify all dependencies are installed
4. Ensure ports 8001-8006 are available

## Version

- **System**: Auralis Backend Services
- **Guardian Version**: 1.0
- **Last Updated**: 2025-10-30
