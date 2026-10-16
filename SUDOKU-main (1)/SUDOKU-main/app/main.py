import os
import sys
from pathlib import Path

# Ensure Google OR-Tools native libraries are initialized on Windows
try:
    import ortools
    from ortools.sat.python import cp_model
except Exception as e:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router as api_router


app = FastAPI(
    title="IO SIGNAL SUDOKU — Industrial I/O Allocation & 3D Digital Twin",
    description="Emerson DeltaV Electronic Marshaling Optimization Platform with Google OR-Tools CP-SAT and Interactive 3D Digital Twin.",
    version="3.5.0"
)

# Enable CORS for flexible integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Mount Static Files
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
def healthcheck():
    return {
        "status": "HEALTHY",
        "service": "IO SIGNAL SUDOKU Optimization Platform",
        "engine": "Google OR-Tools CP-SAT v9.10+",
        "version": "3.5.0"
    }

@app.get("/")
def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "IO SIGNAL SUDOKU API is running. Access API documentation at /docs",
        "health": "/health",
        "api": "/api/project"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
