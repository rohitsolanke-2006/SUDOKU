#!/usr/bin/env python3
"""
IO SIGNAL SUDOKU — Quick Start Server Runner
Runs the FastAPI Backend & Integrated Engineering Console on http://127.0.0.1:8000
"""
import os
import sys
from pathlib import Path

# Set root directory
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Pre-load ortools before server startup
try:
    import ortools
    from ortools.sat.python import cp_model
except Exception as e:
    print(f"Note: OR-Tools initialization warning: {e}")

import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"=================================================================")
    print(f"  IO SIGNAL SUDOKU — Industrial I/O Allocation & 3D Digital Twin  ")
    print(f"  Emerson DeltaV Marshaling Cabinet CAD Workstation              ")
    print(f"=================================================================")
    print(f"  Starting server at: http://{host}:{port}")
    print(f"  Interactive Web Console: http://{host}:{port}/")
    print(f"  Swagger API Documentation: http://{host}:{port}/docs")
    print(f"=================================================================\n")
    uvicorn.run(app, host=host, port=port, reload=False)
