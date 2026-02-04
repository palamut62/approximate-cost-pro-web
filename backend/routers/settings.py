from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from services.settings_service import get_settings_service

router = APIRouter(
    prefix="/settings",
    tags=["Ayarlar"]
)

class SettingsUpdate(BaseModel):
    selected_models: Optional[Dict[str, str]] = None
    filter_free_only: Optional[bool] = None
    llm_warning_threshold: Optional[float] = None
    
    class Config:
        extra = "allow"

@router.get("")
async def get_settings():
    """Get all current settings including cached models"""
    service = get_settings_service()
    return service.get_settings()

@router.post("")
async def update_settings(settings: SettingsUpdate):
    """Update settings"""
    service = get_settings_service()
    
    service = get_settings_service()
    
    # Convert Pydantic model to dict, exclude unset
    update_data = settings.dict(exclude_unset=True)
    
    return service.update_settings(update_data)

@router.post("/refresh-models")
async def refresh_models():
    """Force refresh available AI models from OpenRouter"""
    service = get_settings_service()
    try:
        models = service.refresh_openrouter_models()
        return {"status": "ok", "count": len(models), "models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def get_cached_models():
    """Get only the cached models list"""
    service = get_settings_service()
    settings = service.get_settings()
    return settings.get("cached_models", [])
