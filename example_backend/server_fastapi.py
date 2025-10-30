"""
Example FastAPI server demonstrating proper handling of long-running dataset scan operations.

This example shows how to fix the hanging request issue by:
1. Responding immediately to client
2. Processing scans asynchronously in background
3. Providing status tracking via separate endpoint

Usage:
    pip install fastapi uvicorn
    uvicorn server_fastapi:app --host 0.0.0.0 --port 8006 --reload

Test:
    # Start scan
    curl -X POST http://localhost:8006/api/voice-library/scan-libritts \
        -H "Content-Type: application/json" \
        --data-raw '{"libritts_path": "/path/to/dataset"}'
    
    # Check status (use task_id from above response)
    curl http://localhost:8006/api/voice-library/scan-status/{task_id}
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import uuid
import time
import logging
from typing import Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Library API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task storage (use Redis or database in production)
tasks: Dict[str, dict] = {}


class ScanRequest(BaseModel):
    """Request model for dataset scan"""
    libritts_path: str


class ScanResponse(BaseModel):
    """Response model for scan initiation"""
    task_id: str
    status: str
    message: str


class TaskStatus(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    files_found: Optional[int] = None


def scan_dataset_task(task_id: str, dataset_path: str):
    """
    Background task that performs the actual dataset scanning.
    
    This simulates a long-running operation that would scan
    a LibriTTS dataset directory structure.
    """
    try:
        logger.info(f"Starting scan task {task_id} for path: {dataset_path}")
        
        # Update task status
        tasks[task_id].update({
            "status": "running",
            "started_at": datetime.now().isoformat()
        })
        
        # Simulate dataset scanning
        path = Path(dataset_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {dataset_path}")
        
        # Count files (this would be your actual scanning logic)
        audio_files = list(path.rglob("*.wav"))
        total_files = len(audio_files)
        
        tasks[task_id]["files_found"] = total_files
        tasks[task_id]["message"] = f"Scanning {total_files} audio files"
        
        # Simulate processing with progress updates
        for i, file_path in enumerate(audio_files):
            # Simulate processing time per file
            time.sleep(0.01)  # In real implementation, this would be actual processing
            
            # Update progress
            progress = int((i + 1) / total_files * 100)
            tasks[task_id]["progress"] = progress
            
            # Log progress at intervals
            if progress % 10 == 0:
                logger.info(f"Task {task_id}: {progress}% complete")
        
        # Mark as completed
        tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "completed_at": datetime.now().isoformat(),
            "message": f"Successfully scanned {total_files} files"
        })
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Voice Library API",
        "version": "1.0.0"
    }


@app.post("/api/voice-library/scan-libritts", response_model=ScanResponse)
async def scan_libritts(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Start a LibriTTS dataset scan operation.
    
    This endpoint demonstrates the CORRECT way to handle long-running operations:
    - Validates input immediately
    - Returns response instantly (does not hang)
    - Processes scan in background
    - Client can poll status endpoint for progress
    
    Args:
        request: ScanRequest containing the dataset path
        background_tasks: FastAPI background task manager
        
    Returns:
        ScanResponse with task_id for tracking progress
        
    Raises:
        HTTPException: If path validation fails
    """
    logger.info(f"Received scan request for: {request.libritts_path}")
    
    # Quick validation (fast, synchronous check)
    path = Path(request.libritts_path)
    if not path.exists():
        logger.warning(f"Path not found: {request.libritts_path}")
        raise HTTPException(
            status_code=400,
            detail=f"Path not found: {request.libritts_path}"
        )
    
    if not path.is_dir():
        logger.warning(f"Path is not a directory: {request.libritts_path}")
        raise HTTPException(
            status_code=400,
            detail=f"Path must be a directory: {request.libritts_path}"
        )
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "Scan queued",
        "dataset_path": request.libritts_path
    }
    
    # Queue the background task (non-blocking)
    background_tasks.add_task(scan_dataset_task, task_id, request.libritts_path)
    
    logger.info(f"Task {task_id} queued for background processing")
    
    # Return immediately - THIS FIXES THE HANGING ISSUE
    return ScanResponse(
        task_id=task_id,
        status="accepted",
        message="Scan started in background. Use task_id to check status."
    )


@app.get("/api/voice-library/scan-status/{task_id}", response_model=TaskStatus)
async def get_scan_status(task_id: str):
    """
    Get the status of a scan task.
    
    Args:
        task_id: The unique task identifier returned from scan-libritts endpoint
        
    Returns:
        TaskStatus with current progress and state
        
    Raises:
        HTTPException: If task_id is not found
    """
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    return TaskStatus(**tasks[task_id])


@app.get("/api/voice-library/tasks")
async def list_tasks():
    """List all tasks (for debugging/monitoring)"""
    return {"tasks": list(tasks.values())}


@app.delete("/api/voice-library/scan-status/{task_id}")
async def delete_task(task_id: str):
    """Delete a task from memory"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    deleted_task = tasks.pop(task_id)
    return {"message": f"Task {task_id} deleted", "task": deleted_task}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
