# Guardian Quick Reference Card

## 🚀 Quick Start

### First Time Setup
```powershell
cd Auralis_App
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Start All Services
```powershell
.\start_guardian.ps1
```
**What it does:**
- Starts 5 services in order (8001-8005)
- Monitors health every 30 seconds
- Auto-restarts failures
- Logs to `guardian.log`

### Stop All Services
```powershell
# Press Ctrl+C in Guardian window
```
**OR**
```powershell
.\services_start\stop_all_services.ps1
```

## 🔍 Check Status

### What's Running?
```powershell
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005 }
```

### Check Health
```powershell
Invoke-WebRequest -Uri http://localhost:8001/health | ConvertFrom-Json
Invoke-WebRequest -Uri http://localhost:8002/health | ConvertFrom-Json
# ... etc for 8003, 8004, 8005
```

### View Logs
```powershell
Get-Content guardian.log -Tail 50
Get-Content guardian.log -Tail 50 -Wait  # Follow mode
```

## 🐛 Troubleshooting

### Port Conflicts
```powershell
# 1. Stop everything
.\services_start\stop_all_services.ps1

# 2. Restart Guardian
.\start_guardian.ps1
```

### Service Won't Start
```powershell
# Check what's on the port
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 8001 }

# Kill specific process
$pid = (Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 8001 }).OwningProcess
Stop-Process -Id $pid -Force
```

### Guardian Already Running
```powershell
# Check Guardian port
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -eq 9000 }

# Stop and restart
.\services_start\stop_all_services.ps1
.\start_guardian.ps1
```

## 📊 Services

| Service | Port | Health Endpoint |
|---------|------|-----------------|
| Character Extraction | 8001 | http://localhost:8001/health |
| Document Processor | 8002 | http://localhost:8002/health |
| Query Engine | 8003 | http://localhost:8003/health |
| Metadata Service | 8004 | http://localhost:8004/health |
| RAG Service | 8005 | http://localhost:8005/health |

## ⚠️ Don't Use These

- ❌ `services_start/start_all_services.ps1` - Deprecated
- ✅ `start_guardian.ps1` - Use this instead

## 📖 Documentation

- **Quick Start**: `README.md`
- **Deep Dive**: `docs/services/guardian_startup_flow.md`
- **Validation**: Run `python validate_guardian.py`

## 🆘 Emergency Commands

### Kill All Python Processes
```powershell
Get-Process | Where-Object { $_.ProcessName -like "*python*" } | Stop-Process -Force
```

### Reset Everything
```powershell
# 1. Kill all services
.\services_start\stop_all_services.ps1

# 2. Verify ports are free
Get-NetTCPConnection -State Listen | 
  Where-Object { $_.LocalPort -in 8001..8005,9000 }

# 3. Start fresh
.\start_guardian.ps1
```

## 💡 Tips

- Guardian logs to both console and `guardian.log`
- Health checks run every 30 seconds
- Failed services restart with backoff (5s → 300s)
- Ctrl+C in Guardian window stops everything cleanly
- Use validation script to check system: `python validate_guardian.py`

---

**Need Help?** See `docs/services/guardian_startup_flow.md` for detailed troubleshooting.
