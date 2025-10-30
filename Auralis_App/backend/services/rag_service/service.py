"""
RAG Service
Port: 8005
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Service")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "rag_service",
        "port": 8005
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "rag_service", "status": "running"}

@app.post("/generate")
async def generate_response(data: dict):
    """Generate RAG response"""
    # Placeholder implementation
    return {"response": "Generated response", "context": []}

if __name__ == "__main__":
    logger.info("Starting RAG Service on port 8005")
    uvicorn.run(app, host="0.0.0.0", port=8005, log_level="info")
