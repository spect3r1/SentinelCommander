#!/usr/bin/env python3
import uvicorn
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.getenv("SENTINEL_PORT", "6060"))
    host = os.getenv("SENTINEL_HOST", "0.0.0.0")
    print(f"[*] Starting SentinelCommander Backend on {host}:{port}")
    uvicorn.run("TeamServer.main:app", host=host, port=port, reload=False)
