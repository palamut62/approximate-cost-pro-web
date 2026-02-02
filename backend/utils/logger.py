"""
Centralized Logging Module
Tüm backend servisleri için standart logging sağlar.
"""
import logging
import sys
from typing import Optional
from config import get_log_config

_loggers_cache = {}

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Standart formatta logger oluşturur.

    Args:
        name: Logger adı (genellikle __name__)
        level: Log seviyesi (DEBUG, INFO, WARNING, ERROR). None ise config'den alır.

    Returns:
        Configured logger instance
    """
    if name in _loggers_cache:
        return _loggers_cache[name]

    config = get_log_config()
    logger = logging.getLogger(name)

    # Seviye belirleme
    log_level = level or config.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Handler zaten varsa ekleme
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            fmt=config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (opsiyonel)
        if config.LOG_FILE:
            file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    # Propagation kapatma (duplicate log önleme)
    logger.propagate = False

    _loggers_cache[name] = logger
    return logger


# Kısa kullanım için hazır loggerlar
def get_ai_logger() -> logging.Logger:
    """AI servisi için logger"""
    return setup_logger("ai_service")

def get_vector_logger() -> logging.Logger:
    """Vector DB servisi için logger"""
    return setup_logger("vector_db")

def get_price_logger() -> logging.Logger:
    """Fiyat eşleştirme için logger"""
    return setup_logger("price_match")

def get_validation_logger() -> logging.Logger:
    """Validasyon için logger"""
    return setup_logger("validation")
