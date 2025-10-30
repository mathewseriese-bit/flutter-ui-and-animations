# Dataset Scan Request - Issue Resolution

## Issue Summary

**Title:** Dataset scan request troubleshooting

**Problem:** API endpoint `/api/voice-library/scan-libritts` was hanging after receiving POST request, never returning a response to the client.

**Symptom:**
```bash
curl -X POST http://localhost:8006/api/voice-library/scan-libritts ...
* upload completely sent off: 49 bytes
[hangs indefinitely - no response]
```

## Repository Context

⚠️ **Important Note:** This repository (`flutter-ui-and-animations`) is a Flutter UI/animations showcase and does not contain the actual backend API server that was experiencing the issue.

The documentation and example code provided here serve as:
1. **Reference implementation** showing the correct way to handle the issue
2. **Troubleshooting guide** for similar problems
3. **Educational resource** for async API patterns

## Root Cause

The hanging request issue is typically caused by:

1. **Synchronous long-running operation** - Dataset scanning takes minutes but blocks the HTTP response
2. **No response sent** - Server doesn't return until processing completes
3. **Client timeout** - Connection times out before completion

## Solution

The fix involves implementing **asynchronous background processing**:

1. ✅ Accept request and validate input immediately
2. ✅ Generate unique task ID
3. ✅ Start background worker to process scan
4. ✅ Return task ID instantly (< 1 second)
5. ✅ Provide status endpoint for progress polling

## Documentation Structure

```
.
├── TROUBLESHOOTING_DATASET_SCAN.md     # Detailed troubleshooting guide
│                                       # - Root cause analysis
│                                       # - Multiple solution patterns
│                                       # - Testing approaches
│
└── example_backend/                    # Reference implementation
    ├── README.md                       # Overview and usage
    ├── BEFORE_AFTER.md                 # Visual comparison of problem/solution
    ├── server_fastapi.py               # Working example (FastAPI)
    ├── requirements.txt                # Python dependencies
    └── test_api.sh                     # Test script
```

## Quick Start (Example Server)

To test the fixed implementation:

```bash
# 1. Install dependencies
cd example_backend
pip install -r requirements.txt

# 2. Start server
uvicorn server_fastapi:app --host 0.0.0.0 --port 8006

# 3. Test (in another terminal)
./test_api.sh
```

### Expected Behavior (Fixed)

```bash
# Request returns immediately
$ curl -X POST http://localhost:8006/api/voice-library/scan-libritts \
    -H "Content-Type: application/json" \
    --data-raw '{"libritts_path": "/tmp"}'

# Response (< 1 second):
{
  "task_id": "abc-123-def-456",
  "status": "accepted",
  "message": "Scan started in background"
}

# Poll for progress
$ curl http://localhost:8006/api/voice-library/scan-status/abc-123-def-456
{
  "task_id": "abc-123-def-456",
  "status": "running",
  "progress": 45,
  "files_found": 1000
}
```

## Key Implementation Points

### 1. Immediate Response Pattern

```python
@app.post("/api/voice-library/scan-libritts")
async def scan_libritts(request: ScanRequest, background_tasks: BackgroundTasks):
    # Quick validation
    validate_path(request.libritts_path)
    
    # Generate task ID
    task_id = generate_uuid()
    
    # Queue background work
    background_tasks.add_task(scan_dataset_task, task_id, request.libritts_path)
    
    # Return immediately - THIS FIXES THE HANG
    return {"task_id": task_id, "status": "accepted"}
```

### 2. Background Processing

```python
async def scan_dataset_task(task_id: str, path: str):
    # Long-running work
    for file in scan_files(path):
        process_file(file)
        update_progress(task_id, current_progress)
```

### 3. Status Tracking

```python
@app.get("/api/voice-library/scan-status/{task_id}")
async def get_scan_status(task_id: str):
    return get_task_status(task_id)
```

## Comparison

| Aspect | Before (Broken) | After (Fixed) |
|--------|----------------|---------------|
| **Request Duration** | Minutes or timeout | < 1 second |
| **Client Experience** | Hangs/freezes | Immediate response |
| **Progress Tracking** | None | Real-time via polling |
| **Error Visibility** | Hidden/timeout | Clear error messages |
| **Scalability** | Poor | Good |

## Architecture

```
Client Request
     │
     ├─> Immediate Response (task_id)
     │
     └─> Background Worker
             │
             ├─> Scan Dataset
             ├─> Update Progress
             └─> Mark Complete
                      │
                      └─> Client Polls Status
```

## For Actual Implementation

Since the actual backend server is in a different repository:

1. **Locate the backend repository** with the API implementation
2. **Identify the endpoint handler** for `/api/voice-library/scan-libritts`
3. **Apply the async pattern** from `example_backend/server_fastapi.py`
4. **Add status endpoint** for progress tracking
5. **Update client code** to poll for status instead of waiting
6. **Test thoroughly** to ensure no hanging

## Additional Resources

- **Detailed Analysis:** [TROUBLESHOOTING_DATASET_SCAN.md](./TROUBLESHOOTING_DATASET_SCAN.md)
- **Visual Comparison:** [example_backend/BEFORE_AFTER.md](./example_backend/BEFORE_AFTER.md)
- **Working Example:** [example_backend/server_fastapi.py](./example_backend/server_fastapi.py)
- **Test Suite:** [example_backend/test_api.sh](./example_backend/test_api.sh)

## Technologies Used

- **FastAPI** - Modern async Python web framework
- **Uvicorn** - ASGI server
- **Background Tasks** - For async processing
- **Pydantic** - Data validation

## License

This example code is provided for educational and reference purposes.

## Questions?

If you need help applying this fix to your actual backend:
1. Review the example implementation
2. Check the troubleshooting guide
3. Ensure your backend framework supports async/background tasks
4. Test with the provided test script patterns

---

**Status:** ✅ Documentation and reference implementation complete

**Note:** The actual fix must be applied to the backend API repository, not this Flutter UI repository.
