from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from database import DatabaseManager
from pathlib import Path
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/settings", tags=["Settings"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))

class SettingUpdate(BaseModel):
    key: str
    value: str

class SettingsBatchUpdate(BaseModel):
    settings: Dict[str, str]

@router.get("/")
def get_all_settings():
    """Tüm ayarları getir"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = dict(cursor.fetchall())
    conn.close()
    return settings

@router.get("/{key}")
def get_setting(key: str):
    """Belirli bir ayarı getir"""
    value = db.get_setting(key)
    return {"key": key, "value": value}

@router.post("/")
def update_setting(update: SettingUpdate):
    """Tek bir ayarı güncelle"""
    db.set_setting(update.key, update.value)
    return {"message": "Setting updated", "key": update.key, "value": update.value}

@router.post("/batch")
def update_settings_batch(update: SettingsBatchUpdate):
    """Toplu ayar güncelleme"""
    for key, value in update.settings.items():
        db.set_setting(key, value)
    return {"message": f"{len(update.settings)} settings updated"}
