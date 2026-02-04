"""
Backend Configuration Module
Tüm ayarlanabilir parametreleri merkezi bir yerde toplar.
"""
import os
from typing import Dict, Any

# ============================================
# AI ANALYSIS CONFIGURATION
# ============================================

class AnalysisConfig:
    """Analiz sistemi konfigürasyonu"""

    # Direct Lookup eşiği (eğitim verisinde tam eşleşme için)
    DIRECT_LOOKUP_THRESHOLD: float = 0.95

    # Minimum semantic benzerlik skoru (fiyat eşleştirme için)
    MIN_SEMANTIC_SCORE: float = 0.4

    # Vector DB arama sonuç limiti
    VECTOR_SEARCH_LIMIT: int = 50

    # Context token limitleri
    MAX_POZ_CONTEXT_CHARS: int = 8000
    MAX_FEEDBACK_CONTEXT_CHARS: int = 2000
    MAX_TRAINING_RAG_CONTEXT_CHARS: int = 3000
    MAX_TOTAL_CONTEXT_CHARS: int = 12000

    # RAG için top-k benzer örnek sayısı
    RAG_TOP_K: int = 3

    # Fiyat uyarı eşikleri
    HIGH_PRICE_WARNING_THRESHOLD: float = 100000.0  # TL

    # API timeout (saniye)
    API_TIMEOUT: int = 90
    GEMINI_FALLBACK_TIMEOUT: int = 120


class PriceMatchConfig:
    """Fiyat eşleştirme konfigürasyonu"""

    # Benzerlik ağırlıkları
    DESCRIPTION_SIMILARITY_WEIGHT: float = 0.6
    KEYWORD_BONUS_PER_MATCH: float = 0.1
    UNIT_MATCH_BONUS: float = 0.15

    # Ceza/bonus oranları
    MACHINE_POZ_PENALTY: float = 0.3
    TRANSPORT_POZ_BONUS: float = 0.1

    # Minimum eşleşme skoru
    MIN_MATCH_SCORE: float = 0.4


class ValidationConfig:
    """Validasyon konfigürasyonu"""

    # Kalıp miktarı çarpanı (beton miktarı * bu değer = kalıp miktarı)
    FORMWORK_MULTIPLIER: float = 6.0

    # Fire oranları
    STEEL_WASTE_RATE: float = 0.05  # %5
    CONCRETE_WASTE_RATE: float = 0.02  # %2
    FORMWORK_WASTE_RATE: float = 0.10  # %10

    # Tipik sektör oranları (referans) — ton/m³, m²/m³
    REBAR_PER_CONCRETE: tuple = (0.08, 0.15)     # ton/m³ (80-150 kg/m³)
    FORMWORK_PER_CONCRETE: tuple = (5, 8)         # m²/m³
    MORTAR_PER_WALL_M2: tuple = (0.02, 0.05)     # m³/m²

    # Tipik m² fiyat aralıkları (TL, 2025 referans — min, max)
    PRICE_RANGES_PER_M2: Dict[str, tuple] = {
        'duvar':      (1500, 6000),
        'döşeme':     (2500, 8000),
        'betonarme':  (3500, 10000),
        'seramik':    (800, 4000),
        'boya':       (150, 500),
        'sıva':       (800, 3000),
        'çatı':       (2000, 6000),
    }


class LogConfig:
    """Logging konfigürasyonu"""

    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # Log dosyası (opsiyonel)
    LOG_FILE: str = os.environ.get("LOG_FILE", "")


# ============================================
# SINGLETON CONFIG INSTANCE
# ============================================

_config_cache: Dict[str, Any] = {}

def get_analysis_config() -> AnalysisConfig:
    """AnalysisConfig singleton"""
    if "analysis" not in _config_cache:
        _config_cache["analysis"] = AnalysisConfig()
    return _config_cache["analysis"]

def get_price_config() -> PriceMatchConfig:
    """PriceMatchConfig singleton"""
    if "price" not in _config_cache:
        _config_cache["price"] = PriceMatchConfig()
    return _config_cache["price"]

def get_validation_config() -> ValidationConfig:
    """ValidationConfig singleton"""
    if "validation" not in _config_cache:
        _config_cache["validation"] = ValidationConfig()
    return _config_cache["validation"]

def get_log_config() -> LogConfig:
    """LogConfig singleton"""
    if "log" not in _config_cache:
        _config_cache["log"] = LogConfig()
    return _config_cache["log"]
