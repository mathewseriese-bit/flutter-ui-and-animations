"""
Metadata Service
Port: 8004
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Metadata Service")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "metadata_service",
        "port": 8004
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "metadata_service", "status": "running"}

@app.get("/metadata/{item_id}")
async def get_metadata(item_id: str):
    """Get metadata for an item"""
    # Placeholder implementation
    return {"item_id": item_id, "metadata": {}}

if __name__ == "__main__":
    logger.info("Starting Metadata Service on port 8004")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
