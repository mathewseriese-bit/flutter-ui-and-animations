# Example Backend API Server

## ⚠️ Important Note

This example backend is provided as reference for the dataset scan request troubleshooting issue. 

**This Flutter UI repository does not include the actual backend server** that was experiencing the hanging request issue described in the problem statement.

## Purpose

This example demonstrates:
- How to properly handle long-running dataset scan operations
- Asynchronous task processing
- Immediate response patterns
- Progress tracking

## Problem Context

The original issue involved a curl request that would hang:

```bash
curl -X POST http://localhost:8006/api/voice-library/scan-libritts \
  -H "Content-Type: application/json" \
  --data-raw '{"libritts_path": "H:/Voice_Datasets/LibriTTS_R"}'
```

Output showed the request hanging after:
```
* upload completely sent off: 49 bytes
[no response received]
```

## Solution Approach

The example server (`server.py`) demonstrates the correct implementation:
1. Accept request immediately
2. Validate input quickly
3. Start background processing
4. Return task ID instantly
5. Provide status endpoint for polling

## Installation & Usage

See the individual server examples for setup instructions:
- `server_fastapi.py` - FastAPI implementation (recommended)
- `server_flask.py` - Flask implementation

## Related Documentation

For detailed troubleshooting information, see:
- [TROUBLESHOOTING_DATASET_SCAN.md](../TROUBLESHOOTING_DATASET_SCAN.md)
