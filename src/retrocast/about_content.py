"""Utilities for loading Retrocast's bundled about text."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import Final

_PACKAGE: Final[str] = __package__ or "retrocast"
_ABOUT_RESOURCE: Final[str] = "ABOUT.md"


@lru_cache(maxsize=1)
def load_about_markdown() -> str:
    """Return the Retrocast about Markdown bundled with the package.

    Returns
    -------
    str
        The contents of ``ABOUT.md`` stored alongside the package modules.

    Raises
    ------
    FileNotFoundError
        Raised when the resource cannot be located. This typically indicates
        an installation problem where the package data was not included.
    OSError
        Propagated if the resource cannot be read from the package archive.
    """

    return resources.files(_PACKAGE).joinpath(_ABOUT_RESOURCE).read_text(encoding="utf-8")


__all__ = ["load_about_markdown"]
