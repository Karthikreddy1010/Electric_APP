import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    """Configure structured logging and rotating file handlers."""
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s"
    formatter = logging.Formatter(log_format)

    # Root Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers = []

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Rotating File Handler - Application (INFO+)
    app_handler = RotatingFileHandler(
        log_dir / "application.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)

    # Rotating File Handler - Error (ERROR+)
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # Scheduler Logger Configuration
    scheduler_logger = logging.getLogger("orchestration.scheduler")
    scheduler_logger.setLevel(logging.INFO)
    scheduler_logger.propagate = False  # Prevent duplicate logging to root handler

    # Rotating File Handler - Scheduler (INFO+)
    sched_handler = RotatingFileHandler(
        log_dir / "scheduler.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    sched_handler.setFormatter(formatter)
    sched_handler.setLevel(logging.INFO)
    scheduler_logger.addHandler(sched_handler)

    # Add console handler to scheduler logger as well
    scheduler_logger.addHandler(console_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    logging.info("Logging successfully initialized. Outputs configured for application.log, error.log, and scheduler.log.")
