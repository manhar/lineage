#!/usr/bin/env python3
"""
Power BI Column-Level Data Lineage Application
Single-Port Python Runner (Enterprise & Banking Edition)

Serves both the FastAPI REST backend and pre-compiled React Flow UI
on a single port (default: 8000) using 100% Python dependencies.
"""

import sys
import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(
        description="Run the Power BI Column-Level Data Lineage Service (Python-Only)"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host address to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    print("==================================================================")
    print(" Starting Power BI Lineage Service (100% Python Runtime)         ")
    print(f" Web UI & REST API running on: http://localhost:{args.port}")
    print(f" Swagger API Documentation:   http://localhost:{args.port}/docs")
    print("==================================================================")

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
