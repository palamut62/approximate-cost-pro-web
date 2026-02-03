import threading
import logging
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
from services.training_data_service import TrainingDataService
from routers import ai, projects, analyses, feedback, settings, usage, dashboard, logs
from database import DatabaseManager

app = FastAPI(title="Approximate Cost API", version="1.0.0")

# CORS Setup - MUST be before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(ai.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(analyses.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(usage.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(logs.router, prefix="/api")

# Global Data Cache
POZ_DATA = {}
LOADED_FILES = []
TRAINING_DATA_SERVICE = None

@app.get("/api/health")
async def health_check():
    """Backend health check endpoint"""
    training_stats = TRAINING_DATA_SERVICE.get_stats() if TRAINING_DATA_SERVICE else {'loaded': False}
    vector_status = {}
    if hasattr(app.state, 'vector_db_service') and app.state.vector_db_service:
        vector_status = app.state.vector_db_service.get_status()
    return {
        "status": "ok",
        "poz_count": len(POZ_DATA),
        "files_loaded": len(LOADED_FILES),
        "files": LOADED_FILES,
        "training_data": training_stats,
        "vector_db": vector_status
    }

@app.on_event("startup")
async def startup_event():
    """Start scan on startup"""
    # Run in a separate thread to not block startup
    threading.Thread(target=load_initial_data).start()
    
    # Initialize WebSocket Logging Bridge
    from routers.logs import get_log_handler
    ws_handler = get_log_handler()
    
    # Configure root logger to include WS handler
    root_logger = logging.getLogger()
    
    # Use the same format as defined in config
    from config import get_log_config
    config = get_log_config()
    formatter = logging.Formatter(fmt=config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)
    ws_handler.setFormatter(formatter)
    
    root_logger.addHandler(ws_handler)
    print("WebSocket Logging Bridge initialized.")

def load_initial_data():
    global POZ_DATA, LOADED_FILES, TRAINING_DATA_SERVICE
    print("Loading initial data...")

    # 1. Load Data from multiple sources
    all_data = {}
    all_files = []
    
    # Check ANALIZ folder (Detailed Analysis)
    analiz_folder = Path(__file__).parent.parent / "ANALIZ"
    if analiz_folder.exists():
        print(f"Scanning ANALIZ folder: {analiz_folder}")
        loader = CSVLoader(analiz_folder)
        data, count, files = loader.run()
        all_data.update(data)
        all_files.extend(files)
        print(f"Loaded {count} items from ANALIZ.")
        
    # Check PDF folder (Unit Prices)
    pdf_folder = Path(__file__).parent.parent / "PDF"
    if pdf_folder.exists():
        print(f"Scanning PDF folder: {pdf_folder}")
        loader = CSVLoader(pdf_folder)
        data, count, files = loader.run()
        
        # Merge robustly (Don't overwrite existing keys unless new one has more info?)
        # For now, just setdefault to prefer ANALIZ (first load)
        merged_count = 0
        for k, v in data.items():
            if k not in all_data:
                all_data[k] = v
                merged_count += 1
            # else: keep ANALIZ version as it might be from the detailed analysis file
                
        all_files.extend(files)
        print(f"Loaded {count} items from PDF ({merged_count} new unique items merged).")

    POZ_DATA = all_data
    LOADED_FILES = all_files

    # 2. Load Training Data (JSONL eğitim verisi)
    training_file = Path(__file__).parent.parent / "egitim_verisi_FINAL_READY.jsonl"
    TRAINING_DATA_SERVICE = TrainingDataService(str(training_file))

    # 3. Ayrıca app.state'e de kaydet (router erişimi için)
    app.state.poz_data = all_data
    app.state.loaded_files = all_files
    app.state.training_data_service = TRAINING_DATA_SERVICE

    print(f"✅ Loaded {len(all_data)} items from {len(all_files)} files.")
    training_stats = TRAINING_DATA_SERVICE.get_stats()
    print(f"✅ Loaded {training_stats.get('total_examples', 0)} training examples.")

    # 4. Vector DB (Lazy Loading Mode)
    from services.vector_db_service import VectorDBService
    vector_service = VectorDBService()
    app.state.vector_db_service = vector_service
    # İlk AI analizi yapıldığında otomatik olarak ingestion başlayacak
    app.state.poz_data_for_vector = list(all_data.values())
    print(f"[VECTOR_DB] Lazy mode aktif. İlk AI analizinde {len(all_data)} poz yüklenecek.")

@app.get("/")
def read_root():
    return {"message": "Approximate Cost API is running"}

@app.get("/api/data/status")
def get_data_status():
    poz_data = getattr(app.state, 'poz_data', {})
    loaded_files = getattr(app.state, 'loaded_files', [])
    return {
        "item_count": len(poz_data),
        "file_count": len(loaded_files),
        "files": loaded_files
    }

@app.get("/api/data/search")
def search_poz(q: str):
    """Search for poz items (fast, no PDF scans)"""
    poz_data = getattr(app.state, 'poz_data', {})
    results = []
    if not q:
        return []
    
    q_lower = q.lower()
    for poz in poz_data.values():
        if (q_lower in poz['poz_no'].lower() or 
            q_lower in poz['description'].lower() or 
            q_lower in poz['institution'].lower()):
            
            # Sadece temel veriyi döndür, PDF taraması yapma!
            results.append(poz)
            if len(results) >= 50: # Limit results
                break
    return results

@app.get("/api/data/poz/{poz_no}")
def get_poz_details(poz_no: str):
    """Get detailed info for a single poz (includes PDF scans)"""
    poz_data = getattr(app.state, 'poz_data', {})
    if poz_no not in poz_data:
        raise HTTPException(status_code=404, detail="Poz bulunamadı")
    
    poz = poz_data[poz_no].copy()
    
    from services.local_pdf_service import get_local_pdf_service
    pdf_service = get_local_pdf_service()
    
    # Teknik tarif ve yapısal analiz bilgisini çek
    poz['analysis_data'] = pdf_service.get_description(poz_no, return_structured=True)
    poz['technical_description'] = pdf_service.get_description(poz_no, return_structured=False)
    
    return poz

@app.post("/api/vector-db/ingest")
async def trigger_vector_ingestion():
    """Manuel olarak Vector DB ingestion başlat"""
    if not hasattr(app.state, 'vector_db_service') or not app.state.vector_db_service:
        return {"status": "error", "message": "Vector DB servisi bulunamadı"}

    vector_service = app.state.vector_db_service

    if vector_service._ingestion_started:
        return {
            "status": "already_started",
            "message": "Ingestion zaten başlamış",
            **vector_service.get_status()
        }

    if hasattr(app.state, 'poz_data_for_vector'):
        vector_service.lazy_ingest(app.state.poz_data_for_vector)
        return {
            "status": "started",
            "message": f"{len(app.state.poz_data_for_vector)} poz için ingestion başlatıldı"
        }

    return {"status": "error", "message": "Poz verisi bulunamadı"}

@app.get("/api/vector-db/status")
async def get_vector_db_status():
    """Vector DB durumunu döndür"""
    if not hasattr(app.state, 'vector_db_service') or not app.state.vector_db_service:
        return {"status": "not_initialized", "ready": False}
    return app.state.vector_db_service.get_status()
