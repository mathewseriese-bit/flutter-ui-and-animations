# Dataset Scan Request Troubleshooting

## Issue Description

The API endpoint `/api/voice-library/scan-libritts` appears to hang after receiving the POST request without returning a response.

### Observed Behavior

```bash
curl.exe -v -X POST http://localhost:8006/api/voice-library/scan-libritts \
  -H "Content-Type: application/json" \
  --data-raw '{"libritts_path": "H:/Voice_Datasets/LibriTTS_R"}'
```

**Output:**
```
* upload completely sent off: 49 bytes
[hangs here - no response]
```

## Root Cause Analysis

When an API request hangs after the data is uploaded, the typical causes are:

1. **Missing Response**: The server handler doesn't send a response back to the client
2. **Long-Running Operation**: The scanning operation is synchronous and takes too long
3. **Missing Timeout**: No timeout configured for the operation
4. **Error Handling**: An exception occurs but isn't caught/logged
5. **Database/File Lock**: The operation waits indefinitely on a resource

## Common Solutions

### Solution 1: Implement Asynchronous Processing

For long-running operations like dataset scanning, use asynchronous task processing:

**Python (FastAPI/Flask example):**
```python
from fastapi import BackgroundTasks

@app.post("/api/voice-library/scan-libritts")
async def scan_libritts(request: ScanRequest, background_tasks: BackgroundTasks):
    # Validate the path immediately
    if not os.path.exists(request.libritts_path):
        raise HTTPException(status_code=400, detail="Path not found")
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Start scanning in background
    background_tasks.add_task(perform_scan, task_id, request.libritts_path)
    
    # Return immediately
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Scanning started in background"
    }

def perform_scan(task_id: str, path: str):
    try:
        # Actual scanning logic here
        # Update task status in database/cache
        pass
    except Exception as e:
        # Log error and update task status
        logger.error(f"Scan failed: {e}")
```

### Solution 2: Add Streaming Response

For operations that need to show progress:

```python
from fastapi.responses import StreamingResponse

@app.post("/api/voice-library/scan-libritts")
async def scan_libritts(request: ScanRequest):
    async def generate_progress():
        try:
            yield json.dumps({"status": "started"}) + "\n"
            
            # Perform scanning with progress updates
            for progress in scan_dataset(request.libritts_path):
                yield json.dumps({
                    "status": "processing",
                    "progress": progress
                }) + "\n"
            
            yield json.dumps({"status": "completed"}) + "\n"
        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="application/x-ndjson"
    )
```

### Solution 3: Ensure Immediate Response

At minimum, always return a response immediately:

```python
@app.post("/api/voice-library/scan-libritts")
async def scan_libritts(request: ScanRequest):
    try:
        # Validate input
        if not os.path.exists(request.libritts_path):
            return {"error": "Path not found"}, 400
        
        # Quick validation response
        return {
            "status": "received",
            "message": "Request received, processing...",
            "path": request.libritts_path
        }
        
        # OR trigger async processing and return
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}, 500
```

### Solution 4: Add Timeout Configuration

Configure request/operation timeouts:

**Server-side (FastAPI):**
```python
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=30.0)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"error": "Request timeout"}
            )
```

**Client-side:**
```bash
curl --max-time 30 -X POST http://localhost:8006/api/voice-library/scan-libritts \
  -H "Content-Type: application/json" \
  --data-raw '{"libritts_path": "H:/Voice_Datasets/LibriTTS_R"}'
```

## Recommended Implementation

For a dataset scanning endpoint, the best approach is:

1. **Accept the request immediately** and validate the path
2. **Start scanning in background** using async task queue
3. **Return a task ID** that clients can poll
4. **Provide a status endpoint** to check progress

### Example Implementation

```python
# models.py
class ScanRequest(BaseModel):
    libritts_path: str

class ScanResponse(BaseModel):
    task_id: str
    status: str
    message: str

# main.py
tasks = {}  # In production, use Redis or database

@app.post("/api/voice-library/scan-libritts", response_model=ScanResponse)
async def scan_libritts(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start a LibriTTS dataset scan in the background"""
    
    # Validate path
    if not os.path.exists(request.libritts_path):
        raise HTTPException(status_code=400, detail=f"Path not found: {request.libritts_path}")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending", "progress": 0}
    
    # Queue background task
    background_tasks.add_task(scan_dataset_task, task_id, request.libritts_path)
    
    return ScanResponse(
        task_id=task_id,
        status="accepted",
        message="Scan started in background"
    )

@app.get("/api/voice-library/scan-status/{task_id}")
async def get_scan_status(task_id: str):
    """Check the status of a scan task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

async def scan_dataset_task(task_id: str, path: str):
    """Background task to scan the dataset"""
    try:
        tasks[task_id]["status"] = "running"
        
        # Perform actual scanning
        files = list(Path(path).rglob("*.wav"))
        total = len(files)
        
        for i, file in enumerate(files):
            # Process file
            process_audio_file(file)
            
            # Update progress
            tasks[task_id]["progress"] = int((i + 1) / total * 100)
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        
    except Exception as e:
        logger.error(f"Scan failed for task {task_id}: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
```

## Testing

After implementing the fix, test with:

```bash
# Start scan
response=$(curl -X POST http://localhost:8006/api/voice-library/scan-libritts \
  -H "Content-Type: application/json" \
  --data-raw '{"libritts_path": "H:/Voice_Datasets/LibriTTS_R"}')

# Extract task ID
task_id=$(echo $response | jq -r '.task_id')

# Check status
curl http://localhost:8006/api/voice-library/scan-status/$task_id
```

## Notes

- This repository is a Flutter UI/animations showcase and doesn't contain the backend API code
- If you're looking to fix the actual API, you'll need to locate the backend server repository
- The solutions above are generic patterns that apply to most web frameworks (FastAPI, Flask, Express.js, etc.)

## Related Issues

- Request timeout issues
- Long-running operations in web APIs
- Asynchronous task processing

---

**Status**: This is a troubleshooting guide. The actual fix needs to be implemented in the backend API repository.
