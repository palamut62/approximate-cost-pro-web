from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from typing import List, Literal
import shutil
from pathlib import Path
import os
import logging

router = APIRouter(
    prefix="/files",
    tags=["Dosya Yönetimi"]
)

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
ANALIZ_DIR = BASE_DIR / "ANALIZ"
PDF_DIR = BASE_DIR / "PDF"

# Ensure directories exist
ANALIZ_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    request: Request,
    files: List[UploadFile] = File(...),
    type: Literal['analysis', 'price'] = 'analysis'
):
    """
    Dosya yükle (Analiz veya Birim Fiyat).
    type='analysis' -> ANALIZ klasörüne (PDF)
    type='price' -> PDF klasörüne (Birim Fiyatlar - CSV/PDF)
    """
    target_dir = ANALIZ_DIR if type == 'analysis' else PDF_DIR
    saved_files = []
    
    try:
        for file in files:
            # Güvenlik: Dosya isrini temizle (basitçe)
            filename = os.path.basename(file.filename)
            file_path = target_dir / filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            saved_files.append(filename)
            logger.info(f"[UPLOAD] Dosya kaydedildi: {file_path}")

        # Otomatik sync tetikle (Kullanıcı beklememesi için background task)
        # background_tasks.add_task(trigger_data_reload, request)
        
        return {
            "status": "success", 
            "message": f"{len(saved_files)} dosya yüklendi",
            "files": saved_files,
            "target_dir": str(target_dir.name)
        }
        
    except Exception as e:
        logger.error(f"[UPLOAD ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def perform_full_sync(app: Request):
    """
    Hem CSV verilerini yükler hem de Vector DB'yi günceller.
    """
    logger.info("[SYNC] Tam senkronizasyon başlatıldı...")
    
    # 1. CSV ve dosya sistemini tara (main.py'deki reload_data_func)
    if hasattr(app.state, 'reload_data_func'):
        await app.state.reload_data_func()
    
    # 2. Vector DB güncellemesini tetikle
    if hasattr(app.state, 'vector_db_service') and hasattr(app.state, 'poz_data_for_vector'):
        logger.info("[SYNC] Vector DB güncellemesi tetikleniyor (User Triggered)...")
        # _ingestion_started flag'ini manuel resetle ki tekrar çalışabilsin
        app.state.vector_db_service._ingestion_started = False 
        app.state.vector_db_service.lazy_ingest(app.state.poz_data_for_vector)
    
    logger.info("[SYNC] Tam senkronizasyon tamamlandı.")

@router.post("/sync")
async def trigger_sync(request: Request, background_tasks: BackgroundTasks):
    """
    Veritabanı senkronizasyonunu tetikle.
    Değişen dosyaları tarar ve belleğe yükler.
    """
    if hasattr(request.app.state, 'reload_data_func'):
        # Arka planda çalıştır (yeni helper fonksiyonu ile)
        background_tasks.add_task(perform_full_sync, request.app)
        return {"status": "started", "message": "Tam veri senkronizasyonu başlatıldı (CSV + Vector DB). Terminali takip edin."}
    else:
        raise HTTPException(status_code=500, detail="Reloader fonksiyonu bulunamadı")

@router.get("/list")
async def list_files():
    """Yüklü dosyaları listele"""
    
    def scan_dir(directory: Path):
        files = []
        if directory.exists():
            for f in directory.glob("*.*"):
                if f.is_file() and f.name != ".gitkeep":
                   stat = f.stat()
                   files.append({
                       "name": f.name,
                       "size": stat.st_size,
                       "modified": stat.st_mtime
                   })
        return files

    return {
        "analysis": scan_dir(ANALIZ_DIR),
        "prices": scan_dir(PDF_DIR)
    }

@router.get("/vector-status")
async def get_vector_status(request: Request):
    """Vector DB durumunu döndürür (model olmadan, sadece client bağlantısı ile)."""
    if hasattr(request.app.state, 'vector_db_service'):
        service = request.app.state.vector_db_service
        status = service.get_status()
        count = status.get("document_count", 0)
        feedback_count = status.get("feedback_count", 0)
        return {
            "is_ready": count > 0,
            "count": count,
            "feedback_count": feedback_count,
            "model_loaded": status.get("model_loaded", False),
            "message": f"Vector DB {'Hazır' if count > 0 else 'Boş'} ({count} kayıt)"
        }

    return {
        "is_ready": False,
        "count": 0,
        "feedback_count": 0,
        "model_loaded": False,
        "message": "Vector DB servis başlatılmadı"
    }
