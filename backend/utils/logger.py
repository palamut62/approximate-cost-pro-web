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

        # WebSocket handler entegrasyonu
        # main.py'de root logger'a eklendiği için propagate=True ile root'a ulaşacaktır.
        # Ancak çocuk logger'larda propagate=True bırakmak bazen duplicate loglara sebep olabilir.
        # En güvenli yol, eğer propagate False olacaksa bile WS handler'ı buraya eklemektir.
        
        # Bridge zaten kurulmuş mu kontrol et
        found_ws = False
        # Root logger'daki handler'ları tara
        root_logger = logging.getLogger()
        for h in root_logger.handlers:
            if h.__class__.__name__ == 'WebSocketLogHandler':
                h.setFormatter(formatter)
                logger.addHandler(h)
                found_ws = True
                break
        
        # Eğer root'ta yoksa (henüz main.py çalışmadıysa), 
        # log akışı başladığında eklenebilmesi için propagate=True bırakıyoruz.
        if found_ws:
            logger.propagate = False
        else:
            logger.propagate = True

    # Propagation durumu yukarıdaki mantığa göre ayarlandığı için burayı kaldırıyoruz

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

def get_db_logger() -> logging.Logger:
    """Veritabanı işlemleri için logger"""
    return setup_logger("database")

def get_pdf_logger() -> logging.Logger:
    """PDF işleme işlemleri için logger"""
    return setup_logger("pdf_engine")

def get_training_logger() -> logging.Logger:
    """Eğitim verisi işlemleri için logger"""
    return setup_logger("training_service")

def get_general_logger() -> logging.Logger:
    """Genel sistem işlemleri için logger"""
    return setup_logger("general")
