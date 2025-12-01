"""Offline-friendly subset of ``loguru-config``.

This shim provides a minimal ``LoguruConfig`` implementation that supports
loading configuration dictionaries or JSON files and applying them via
``loguru.logger.configure``. It is intentionally small to allow development
and testing in restricted environments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from loguru import logger

ConfigMapping = Mapping[str, Any]


class LoguruConfig:
    """Apply loguru configuration from a mapping or JSON file."""

    @staticmethod
    def _load_from_path(config_path: Path) -> ConfigMapping:
        with config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def load(cls, config: ConfigMapping | str | Path, *, inplace: bool = True) -> ConfigMapping:
        """Load configuration and apply it to the loguru logger.

        Args:
            config: A mapping or a path to a JSON configuration file.
            inplace: Retained for API compatibility; unused here.

        Returns:
            The parsed configuration mapping.
        """

        if isinstance(config, (str, Path)):
            config_mapping: ConfigMapping = cls._load_from_path(Path(config))
        elif isinstance(config, MutableMapping):
            config_mapping = config
        else:
            raise TypeError("config must be a mapping or a path to a JSON file")

        logger.configure(**config_mapping)
        return config_mapping


__all__ = ["LoguruConfig"]
