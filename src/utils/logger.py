import os
import logging
from logging.handlers import RotatingFileHandler
from src.utils.config import APP_DIR

def setup_logger():
    """Sets up a rolling file logger and standard console logger."""
    os.makedirs(APP_DIR, exist_ok=True)
    log_path = os.path.join(APP_DIR, "academyos.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is called multiple times
    if root_logger.handlers:
        return
        
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Rolling File Handler (5 MB per file, max 5 backups)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    logging.info("Logger initialized successfully.")
