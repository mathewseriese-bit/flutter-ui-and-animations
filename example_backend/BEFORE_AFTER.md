# Before & After: Fixing the Hanging Request Issue

## The Problem

### Before (Hanging Request)

```python
@app.post("/api/voice-library/scan-libritts")
def scan_libritts(request: ScanRequest):
    # ❌ PROBLEM: Long-running operation blocks the request
    path = Path(request.libritts_path)
    files = list(path.rglob("*.wav"))
    
    results = []
    for file in files:
        # This takes a long time...
        result = process_audio_file(file)
        results.append(result)
    
    # Response is never sent until ALL processing completes
    # If this takes minutes, the client sees nothing and times out
    return {"status": "completed", "results": results}
```

**What happens:**
1. Client sends POST request
2. Server receives request: `* upload completely sent off: 49 bytes`
3. Server starts processing (takes minutes)
4. **Client waits indefinitely** ← Request appears hung
5. Eventually: timeout error OR very late response

**Client experience:**
```bash
$ curl -X POST http://localhost:8006/api/voice-library/scan-libritts ...
* upload completely sent off: 49 bytes
[waiting... waiting... waiting...]  # ← HUNG HERE
# Eventually: curl: (28) Operation timed out
```

---

## The Solution

### After (Immediate Response + Background Processing)

```python
@app.post("/api/voice-library/scan-libritts")
async def scan_libritts(request: ScanRequest, background_tasks: BackgroundTasks):
    # ✅ Quick validation (fast)
    path = Path(request.libritts_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail="Path not found")
    
    # ✅ Generate task ID
    task_id = str(uuid.uuid4())
    
    # ✅ Queue background processing (non-blocking)
    background_tasks.add_task(scan_dataset_task, task_id, request.libritts_path)
    
    # ✅ Return immediately - THIS IS THE FIX
    return {
        "task_id": task_id,
        "status": "accepted",
        "message": "Scan started in background"
    }

# Background function runs asynchronously
async def scan_dataset_task(task_id: str, path: str):
    # Long-running work happens here
    # Updates task status in database/cache
    pass
```

**What happens:**
1. Client sends POST request
2. Server receives request
3. Server validates path (< 100ms)
4. **Server returns immediately** ← Request completes instantly
5. Background worker continues processing
6. Client can poll status with task_id

**Client experience:**
```bash
$ curl -X POST http://localhost:8006/api/voice-library/scan-libritts ...
* upload completely sent off: 49 bytes
# ✓ Immediate response (< 1 second)
{
  "task_id": "abc-123-def-456",
  "status": "accepted",
  "message": "Scan started in background"
}

# Check progress
$ curl http://localhost:8006/api/voice-library/scan-status/abc-123-def-456
{
  "task_id": "abc-123-def-456",
  "status": "running",
  "progress": 45,
  "message": "Processing file 450/1000"
}
```

---

## Key Differences

| Aspect | Before (Blocking) | After (Async) |
|--------|------------------|---------------|
| **Response Time** | Minutes (or timeout) | < 1 second |
| **Client Hangs** | Yes ❌ | No ✅ |
| **Progress Tracking** | No | Yes ✅ |
| **User Experience** | Poor - appears broken | Good - clear feedback |
| **Scalability** | Poor - blocks threads | Good - handles many requests |
| **Error Handling** | Client may never see errors | Clear error responses |

---

## Testing the Fix

### Step 1: Start the Fixed Server

```bash
cd example_backend
pip install -r requirements.txt
uvicorn server_fastapi:app --host 0.0.0.0 --port 8006
```

### Step 2: Test the Endpoint

```bash
# This now returns immediately (not hung)
curl -v -X POST http://localhost:8006/api/voice-library/scan-libritts \
  -H "Content-Type: application/json" \
  --data-raw '{"libritts_path": "/tmp"}'

# Expected output (immediate):
{
  "task_id": "some-uuid",
  "status": "accepted",
  "message": "Scan started in background. Use task_id to check status."
}

# Check status
curl http://localhost:8006/api/voice-library/scan-status/some-uuid
```

### Step 3: Compare Timing

**Before:** Request hangs for minutes or times out
**After:** Request completes in < 1 second

---

## Implementation Checklist

To fix a hanging long-running endpoint:

- [ ] Identify the slow operation
- [ ] Extract slow code into background task function
- [ ] Add task ID generation (UUID)
- [ ] Add task status storage (dict/Redis/DB)
- [ ] Create background task with `background_tasks.add_task()`
- [ ] Return immediate response with task_id
- [ ] Create status endpoint for polling
- [ ] Update task status as processing progresses
- [ ] Handle errors and update task accordingly
- [ ] Test with actual curl/client to verify no hanging

---

## Architecture Pattern

```
┌─────────┐                    ┌─────────┐
│ Client  │                    │ Server  │
└────┬────┘                    └────┬────┘
     │                              │
     │ 1. POST /scan-libritts       │
     │─────────────────────────────>│
     │                              │ 2. Validate quickly
     │                              │ 3. Create task_id
     │                              │ 4. Queue background job
     │                              │
     │ 5. Response with task_id     │
     │<─────────────────────────────│
     │                              │
     │                         ┌────┴────┐
     │                         │ Worker  │
     │                         │ Process │
     │                         └────┬────┘
     │                              │ 6. Scan dataset
     │                              │ 7. Update status
     │                              │
     │ 8. GET /scan-status/:id      │
     │─────────────────────────────>│
     │                              │ 9. Read status
     │ 10. Current progress         │
     │<─────────────────────────────│
     │                              │
     
Request completes in step 5 (< 1 sec)
Processing continues in steps 6-7 (minutes)
Client polls for updates in steps 8-10
```

---

## Additional Resources

- **Full Implementation:** See `example_backend/server_fastapi.py`
- **Test Script:** Run `example_backend/test_api.sh`
- **Detailed Troubleshooting:** See `TROUBLESHOOTING_DATASET_SCAN.md`

---

## Summary

**The root cause:** Synchronous long-running operation blocking HTTP response

**The fix:** Asynchronous background processing with immediate response

**The result:** Request completes instantly, client can track progress
