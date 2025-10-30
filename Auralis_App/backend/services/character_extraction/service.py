"""
Character Extraction Service
Port: 8001
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Character Extraction Service")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "character_extraction",
        "port": 8001
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "character_extraction", "status": "running"}

@app.post("/extract")
async def extract_characters(data: dict):
    """Extract characters from text"""
    # Placeholder implementation
    return {"extracted": "sample_characters", "count": 0}

if __name__ == "__main__":
    logger.info("Starting Character Extraction Service on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
