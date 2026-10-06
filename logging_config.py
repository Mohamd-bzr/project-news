"""Structured logging configuration for FreeBuff.
Usage:
    from logging_config import setup_logging, get_logger
    setup_logging(log_dir='logs', level=logging.INFO)
    log = get_logger(__name__)
"""
import logging
import logging.handlers
import os
import json
import time
from pathlib import Path


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        return json.dumps(log_entry, ensure_ascii=False)


class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            if self.stream is None or getattr(self.stream, "closed", False):
                return
            super().emit(record)
        except (ValueError, OSError):
            pass


def setup_logging(log_dir="logs", level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """Setup file + console logging."""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # third-party parse noise: trafilatura logs ERROR for every page it
    # cannot parse (dead paywalls, empty shells) — expected, not actionable
    logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

    if any(getattr(h, "_freebuff_handler", False) for h in root.handlers):
        return

    # Console handler (human-readable)
    console = SafeStreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    console._freebuff_handler = True
    root.addHandler(console)

    # File handler (JSON, rotated)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "freebuff.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler._freebuff_handler = True
    root.addHandler(file_handler)

    # Error-only file
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "freebuff_error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler._freebuff_handler = True
    root.addHandler(error_handler)


def get_logger(name):
    return logging.getLogger(name)
