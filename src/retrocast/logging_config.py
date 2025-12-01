"""Centralized logging configuration for Retrocast."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, MutableMapping, Optional

from loguru import logger as _logger
from loguru_config.loguru_config import LoguruConfig  # type: ignore[import-untyped]

DEFAULT_CONFIG_FILENAME = "logging.json"
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


def _default_loguru_config(level: str, log_file: Optional[Path]) -> dict:
    """Build a default loguru configuration dictionary."""

    handlers = [
        {
            "sink": sys.stderr,
            "level": level,
            "format": _format_record,
            "colorize": True,
            "backtrace": False,
            "diagnose": False,
        }
    ]

    if log_file is not None:
        if not log_file.parent.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            {
                "sink": log_file,
                "level": level,
                "format": _format_record,
                "backtrace": False,
                "diagnose": False,
                "enqueue": True,
            }
        )

    return {
        "handlers": handlers,
        "extra": {"logger_name": "retrocast"},
    }


def _load_external_config(config_path: Path) -> bool:
    """Load configuration from a file if it exists."""

    if config_path.is_file():
        LoguruConfig.load(config_path)
        return True
    return False


def setup_logging(
    app_dir: Path,
    *,
    verbose: bool = False,
    log_file: Optional[Path] = None,
    enable_file_logging: bool | None = None,
) -> None:
    """Configure loguru logging for the application.

    External configuration can be supplied via the ``RETROCAST_LOG_CONFIG``
    environment variable or by placing a ``logging.json`` file in the
    application directory.
    """

    level = "DEBUG" if verbose else "INFO"
    _logger.remove()

    config_file = os.getenv("RETROCAST_LOG_CONFIG")
    if config_file and _load_external_config(Path(config_file)):
        return

    if _load_external_config(app_dir / DEFAULT_CONFIG_FILENAME):
        return

    file_sink = log_file if enable_file_logging else None
    LoguruConfig.load(_default_loguru_config(level, file_sink), inplace=True)


def get_logger(name: Optional[str] = None):
    """Return a logger instance bound to the provided name."""

    if name:
        return _logger.bind(logger_name=name)
    return _logger


__all__ = ["get_logger", "setup_logging"]
