from fastapi import APIRouter, Request
from database import DatabaseManager
from pathlib import Path

router = APIRouter(prefix="/data", tags=["Dashboard"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))

@router.get("/status")
def get_status(request: Request):
    """Dashboard istatistiklerini getir"""
    # DB Stats
    stats = db.get_dashboard_stats()
    
    # In-Memory Stats (Loaded Items)
    poz_data = getattr(request.app.state, 'poz_data', {})
    loaded_files = getattr(request.app.state, 'loaded_files', [])
    
    # Override item_count with the loaded reference items count (User expectation)
    # The DB returned 'item_count' which was user-created items in projects.
    # We'll preserve that as 'created_item_count' for clarity.
    stats['created_item_count'] = stats.get('item_count', 0)
    
    if not isinstance(loaded_files, list):
        loaded_files = []

    stats['item_count'] = len(poz_data)
    stats['file_count'] = len(loaded_files)
    stats['files'] = loaded_files
    
    # Add status indicator
    stats['status'] = 'ready' if stats['file_count'] > 0 else 'no_data'
    
    return stats

