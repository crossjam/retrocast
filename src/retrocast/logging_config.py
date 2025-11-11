"""Centralized logging configuration for Retrocast."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, MutableMapping, Optional

from loguru import logger as _logger

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[logger_name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

if TYPE_CHECKING:
    from loguru import Record
else:  # pragma: no cover - runtime alias for typing compatibility
    Record = MutableMapping[str, object]


def _format_record(record: "Record") -> str:
    """Build the log line using either the bound name or module name."""

    logger_name = record["extra"].get("logger_name", record["name"])
    record["extra"].setdefault("logger_name", logger_name)
    return LOG_FORMAT


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """Configure loguru logging for the application."""

    level = "DEBUG" if verbose else "INFO"
    _logger.remove()
    _logger.add(
        sys.stderr,
        level=level,
        format=_format_record,
        colorize=True,
        backtrace=False,
        diagnose=False,
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            log_file,
            level=level,
            format=_format_record,
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )


def get_logger(name: Optional[str] = None):
    """Return a logger instance bound to the provided name."""

    if name:
        return _logger.bind(logger_name=name)
    return _logger


__all__ = ["get_logger", "setup_logging"]

