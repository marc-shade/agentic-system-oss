"""Logging configuration for ACD."""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog


_configured = False


def setup_logging(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    daemon_name: str = "acd"
) -> None:
    """Configure structured logging for the daemon.

    Args:
        log_file: Path to log file (None for stdout only)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        daemon_name: Name prefix for log entries
    """
    global _configured

    if _configured:
        return

    # Set up standard logging
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
