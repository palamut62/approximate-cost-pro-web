from fastapi import APIRouter
from database import DatabaseManager
from pathlib import Path

router = APIRouter(prefix="/data", tags=["Dashboard"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))

@router.get("/status")
def get_status():
    """Dashboard istatistiklerini getir"""
    stats = db.get_dashboard_stats()
    return stats

