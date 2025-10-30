"""
Document Processor Service
Port: 8002
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Processor Service")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "document_processor",
        "port": 8002
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "document_processor", "status": "running"}

@app.post("/process")
async def process_document(data: dict):
    """Process documents"""
    # Placeholder implementation
    return {"processed": True, "document_id": "sample"}

if __name__ == "__main__":
    logger.info("Starting Document Processor Service on port 8002")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
