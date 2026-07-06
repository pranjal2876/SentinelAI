"""
Centralized logging configuration using Loguru.

We intercept the standard `logging` module so that libraries (uvicorn,
sqlalchemy, ultralytics) route through the same structured sink.
"""
from __future__ import annotations

import logging
import sys

from loguru import logger

from app.core.config import settings


class _InterceptHandler(logging.Handler):
    """Redirect stdlib logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure Loguru sinks and intercept stdlib loggers."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
    )
    logger.add(
        "logs/sentinelai_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="14 days",
        compression="zip",
        level=settings.LOG_LEVEL,
        enqueue=True,
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [_InterceptHandler()]

    logger.info("Logging initialised (level=%s)" % settings.LOG_LEVEL)


__all__ = ["logger", "setup_logging"]
