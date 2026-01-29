import threading
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / ".env")

# Add backend directory to sys.path and ensure it's first to avoid collisions with root 'core'
backend_dir = str(Path(__file__).parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add root directory for database access
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.data_manager import CSVLoader
from routers import ai, projects, analyses, feedback, settings
from database import DatabaseManager

app = FastAPI(title="Approximate Cost API", version="1.0.0")

# Register Routers
app.include_router(ai.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(analyses.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Data Cache
POZ_DATA = {}
LOADED_FILES = []

@app.on_event("startup")
async def startup_event():
    """Start scan on startup"""
    # Run in a separate thread to not block startup
    threading.Thread(target=load_initial_data).start()

def load_initial_data():
    global POZ_DATA, LOADED_FILES
    print("Loading initial data...")
    # Point to the root PDF folder
    pdf_folder = Path(__file__).parent.parent / "PDF"
    loader = CSVLoader(pdf_folder)
    data, count, files = loader.run()
    POZ_DATA = data
    LOADED_FILES = files
    # Ayrıca app.state'e de kaydet (router erişimi için)
    app.state.poz_data = data
    app.state.loaded_files = files
    print(f"Loaded {count} items from {len(files)} files.")

@app.get("/")
def read_root():
    return {"message": "Approximate Cost API is running"}

@app.get("/api/data/status")
def get_data_status():
    return {
        "item_count": len(POZ_DATA),
        "file_count": len(LOADED_FILES),
        "files": LOADED_FILES
    }

@app.get("/api/data/search")
def search_poz(q: str):
    """Search for poz items"""
    results = []
    if not q:
        return []
    
    q = q.lower()
    for poz in POZ_DATA.values():
        if (q in poz['poz_no'].lower() or 
            q in poz['description'].lower() or 
            q in poz['institution'].lower()):
            results.append(poz)
            if len(results) >= 50: # Limit results
                break
    return results
