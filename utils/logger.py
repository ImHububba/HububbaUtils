# utils/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(path: str, max_bytes: int = 2_000_000, backup_count: int = 5) -> logging.Logger:
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Ensure directory exists (prevents FileNotFoundError)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(fh)

    return logger
