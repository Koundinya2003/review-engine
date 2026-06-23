"""
Structured logging configuration.

Provides centralized logging with support for console and file output,
JSON formatting for production, and correlation IDs for request tracing.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom attributes
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        return json.dumps(log_data)


def configure_logging() -> None:
    """Configure logging based on settings."""
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.getLevelName(settings.logging.level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.getLevelName(settings.logging.level))
    
    if settings.logging.use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(settings.logging.format)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if configured
    if settings.logging.file:
        file_handler = logging.FileHandler(settings.logging.file)
        file_handler.setLevel(logging.getLevelName(settings.logging.level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
