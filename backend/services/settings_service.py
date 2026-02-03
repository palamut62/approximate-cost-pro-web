import json
import os
import requests
import time
import logging
from typing import Dict, Any, List, Optional
from threading import Lock

logger = logging.getLogger("settings_service")

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")

# Default settings structure
DEFAULT_SETTINGS = {
    "selected_models": {
        "analyze": "moonshotai/kimi-k2.5",
        "refine": "moonshotai/kimi-k2.5",
        "critic": "moonshotai/kimi-k2.5"
    },
    "cached_models": [],
    "last_models_refresh": None,
    "filter_free_only": False
}

class SettingsService:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self.settings = self._load_settings()

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = cls()
        return cls._instance

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file or create with defaults."""
        if not os.path.exists(SETTINGS_FILE):
            self._save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()
        
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return DEFAULT_SETTINGS.copy()

    def _save_settings(self, settings: Dict[str, Any]):
        """Save settings to JSON file."""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get_settings(self) -> Dict[str, Any]:
        return self.settings

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update settings and persist."""
        # Deep merge or just replacement? For simplicity, we assume full structure or partial updates at top level
        for key, value in new_settings.items():
            if key == "selected_models" and isinstance(value, dict):
                # Update individual model selections
                self.settings["selected_models"].update(value)
            else:
                self.settings[key] = value
        
        self._save_settings(self.settings)
        return self.settings

    def get_model_for_task(self, task: str) -> str:
        """Get the configured model ID for a specific task."""
        # task: "analyze", "refine", "critic"
        return self.settings.get("selected_models", {}).get(task, DEFAULT_SETTINGS["selected_models"]["analyze"])

    def refresh_openrouter_models(self) -> List[Dict[str, Any]]:
        """Fetch models from OpenRouter and cache them."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not found when refreshing models.")
            return []

        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            models_list = data.get("data", [])

            # Process and simplify model data
            processed_models = []
            for m in models_list:
                pricing = m.get("pricing", {})
                is_free = (
                    float(pricing.get("prompt", 0)) == 0 and 
                    float(pricing.get("completion", 0)) == 0
                )
                
                processed_models.append({
                    "id": m["id"],
                    "name": m.get("name", m["id"]),
                    "context_length": m.get("context_length", 0),
                    "is_free": is_free,
                    "pricing": pricing
                })

            # Update cache
            self.settings["cached_models"] = processed_models
            self.settings["last_models_refresh"] = time.time()
            self._save_settings(self.settings)
            
            return processed_models

        except Exception as e:
            logger.error(f"Failed to refresh OpenRouter models: {e}")
            raise e

def get_settings_service():
    return SettingsService.get_instance()
