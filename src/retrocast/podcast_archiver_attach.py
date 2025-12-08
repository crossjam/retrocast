"""Helpers for attaching the podcast-archiver SQLite database."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from loguru import logger
from podcast_archiver import constants as podcast_archiver_constants
from podcast_archiver.cli import get_default_config_path

from .appdir import get_app_dir

ARCHIVER_ALIAS = "podcast_archiver"
APPDIR_ARCHIVER_DB = "episodes.db"


@dataclass(frozen=True, slots=True)
class AttachedDatabase:
    alias: str
    path: Path
    tables: tuple[str, ...]
    views: tuple[str, ...]
    colliding_objects: tuple[str, ...]


def _candidate_paths() -> tuple[Path, ...]:
    """Return candidate podcast-archiver database paths, ordered by preference."""

    candidates: list[Path] = []

    # Prefer the retrocast-managed episodes.db inside the application directory
    app_dir = get_app_dir(create=False)
    candidates.append((app_dir / APPDIR_ARCHIVER_DB).resolve())

    # Also consider the podcast-archiver default database next to its config
    config_path = get_default_config_path()
    if config_path is None:
        logger.debug("podcast-archiver config path unavailable; skipping attach discovery")
    else:
        candidates.append(
            (config_path.parent / podcast_archiver_constants.DEFAULT_DATABASE_FILENAME).resolve()
        )

    # Remove duplicates while preserving order
    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for path in candidates:
        if path not in seen:
            unique_candidates.append(path)
            seen.add(path)

    return tuple(unique_candidates)


def get_podcast_archiver_db_path() -> Path | None:
    """Return the default podcast-archiver database path, if discoverable."""

    for candidate in _candidate_paths():
        if candidate.exists():
            logger.debug("Found podcast-archiver database candidate at {}", candidate)
            return candidate

        logger.debug("Podcast-archiver database not found at {}", candidate)

    return None


def _existing_database_aliases(conn: sqlite3.Connection) -> set[str]:
    try:
        cursor = conn.execute("pragma database_list")
    except sqlite3.Error:
        return set()
    return {row[1] for row in cursor.fetchall()}


def _choose_alias(conn: sqlite3.Connection, preferred: str = ARCHIVER_ALIAS) -> str:
    aliases = _existing_database_aliases(conn)
    if preferred not in aliases:
        return preferred

    suffix = 1
    while f"{preferred}_{suffix}" in aliases:
        suffix += 1
    resolved_alias = f"{preferred}_{suffix}"
    logger.debug("Alias {} already in use; using {}", preferred, resolved_alias)
    return resolved_alias


def _fetch_objects(
    conn: sqlite3.Connection, alias: str, *, kinds: Sequence[str]
) -> tuple[str, ...]:
    placeholders = ", ".join("?" for _ in kinds)
    try:
        rows = conn.execute(
            f"select name from [{alias}].sqlite_master"
            f" where type in ({placeholders}) order by type, name",
            tuple(kinds),
        ).fetchall()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        logger.debug("Unable to enumerate {} objects for alias {}: {}", kinds, alias, exc)
        return ()
    return tuple(row[0] for row in rows)


def _fetch_main_objects(conn: sqlite3.Connection, *, kinds: Sequence[str]) -> tuple[str, ...]:
    placeholders = ", ".join("?" for _ in kinds)
    try:
        rows = conn.execute(
            f"select name from sqlite_master where type in ({placeholders}) order by type, name",
            tuple(kinds),
        ).fetchall()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        logger.debug("Unable to enumerate main {} objects: {}", kinds, exc)
        return ()
    return tuple(row[0] for row in rows)


def attach_podcast_archiver(conn: sqlite3.Connection) -> AttachedDatabase | None:
    """Attach the podcast-archiver database to the provided connection."""

    archiver_path = get_podcast_archiver_db_path()
    if archiver_path is None:
        return None
    if not archiver_path.exists():
        logger.debug("podcast-archiver database not found at {}", archiver_path)
        return None

    alias = _choose_alias(conn)
    logger.info("Attaching podcast-archiver database from {} as [{}]", archiver_path, alias)
    try:
        conn.execute(f"attach database ? as [{alias}]", (str(archiver_path),))
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        logger.warning("Failed to attach podcast-archiver database at {}: {}", archiver_path, exc)
        return None

    tables = _fetch_objects(conn, alias, kinds=("table",))
    views = _fetch_objects(conn, alias, kinds=("view",))
    main_tables = _fetch_main_objects(conn, kinds=("table",))
    main_views = _fetch_main_objects(conn, kinds=("view",))
    colliding_objects = tuple(sorted(set(tables + views).intersection(main_tables + main_views)))
    logger.info(
        "Attached podcast-archiver database as [{}] with {} tables and {} views",
        alias,
        len(tables),
        len(views),
    )
    if colliding_objects:
        logger.debug("Attached podcast-archiver objects colliding with main: {}", colliding_objects)
    return AttachedDatabase(
        alias=alias,
        path=archiver_path,
        tables=tables,
        views=views,
        colliding_objects=colliding_objects,
    )


def attach_all(conn: sqlite3.Connection, attachments: Iterable[tuple[str, Path]]) -> None:
    """Attach additional databases to the connection."""

    for alias, path in attachments:
        logger.info("Attaching database from {} as [{}]", path, alias)
        try:
            conn.execute(f"attach database ? as [{alias}]", (str(path),))
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            logger.warning("Failed to attach {} at {}: {}", alias, path, exc)
            continue
        logger.info("Attached database from {} as [{}]", path, alias)
