# mypy: disable-error-code="union-attr"

import datetime
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from sqlite_utils import Database
from sqlite_utils.db import Table

from .constants import (
    CHAPTERS,
    CONTENT,
    DESCRIPTION,
    ENCLOSURE_URL,
    EPISODES,
    EPISODES_EXTENDED,
    FEED_ID,
    FEED_XML_URL,
    FEEDS,
    FEEDS_EXTENDED,
    GUID,
    IMAGE,
    INCLUDE_PODCAST_IDS,
    LAST_UPDATED,
    LINK,
    OVERCAST_ID,
    PLAYLISTS,
    PROGRESS,
    PUB_DATE,
    SMART,
    SORTING,
    SOURCE,
    TIME,
    TITLE,
    TRANSCRIPT_DL_PATH,
    TRANSCRIPT_TYPE,
    TRANSCRIPT_URL,
    URL,
    USER_REC_DATE,
    USER_UPDATED_DATE,
    XML_URL,
)


class Datastore:
    """Object responsible for all database interactions."""

    @staticmethod
    def exists(db_path: Path | str) -> bool:
        """Check if the database file exists."""
        return Path(db_path).exists()

    def __init__(self, db_path: Path | str) -> None:
        """Instantiate and ensure tables exist with expected columns."""
        self.db: Database = Database(str(db_path))
        self._prepare_db()

    def _table(self, name: str) -> Table:
        """Return a table handle with narrowed typing."""
        return cast(Table, self.db[name])

    def _connection(self) -> sqlite3.Connection:
        """Return a live SQLite connection for transaction operations."""
        return cast(sqlite3.Connection, self.db.conn)

    def _prepare_db(self) -> None:
        if FEEDS not in self.db.table_names():
            self._table(FEEDS).create(
                {
                    OVERCAST_ID: int,
                    TITLE: str,
                    "subscribed": bool,
                    "overcastAddedDate": datetime.datetime,
                    "notifications": bool,
                    XML_URL: str,
                    "htmlUrl": str,
                    "dateRemoveDetected": datetime.datetime,
                },
                pk=OVERCAST_ID,
            )
        if FEEDS_EXTENDED not in self.db.table_names():
            self._table(FEEDS_EXTENDED).create(
                {
                    XML_URL: str,
                    TITLE: str,
                    DESCRIPTION: str,
                    LAST_UPDATED: datetime.datetime,
                    LINK: str,
                    GUID: str,
                },
                pk=XML_URL,
                foreign_keys=[(XML_URL, FEEDS, XML_URL)],
            )
            self._table(FEEDS_EXTENDED).enable_fts(
                [TITLE, DESCRIPTION],
                create_triggers=True,
            )
        if EPISODES not in self.db.table_names():
            self._table(EPISODES).create(
                {
                    OVERCAST_ID: int,
                    FEED_ID: int,
                    TITLE: str,
                    URL: str,
                    "overcastUrl": str,
                    "played": bool,
                    PROGRESS: int,
                    ENCLOSURE_URL: str,
                    USER_UPDATED_DATE: datetime.datetime,
                    USER_REC_DATE: datetime.datetime,
                    PUB_DATE: datetime.datetime,
                    "userDeleted": bool,
                },
                pk=OVERCAST_ID,
                foreign_keys=[(OVERCAST_ID, FEEDS, OVERCAST_ID)],
            )
        if EPISODES_EXTENDED not in self.db.table_names():
            self._table(EPISODES_EXTENDED).create(
                {
                    ENCLOSURE_URL: str,
                    FEED_XML_URL: str,
                    TITLE: str,
                    DESCRIPTION: str,
                    LINK: str,
                    GUID: str,
                },
                pk=ENCLOSURE_URL,
                foreign_keys=[
                    (ENCLOSURE_URL, EPISODES, ENCLOSURE_URL),
                    (FEED_XML_URL, FEEDS_EXTENDED, XML_URL),
                ],
            )
            self._table(EPISODES_EXTENDED).enable_fts(
                [TITLE, DESCRIPTION],
                create_triggers=True,
            )
        if PLAYLISTS not in self.db.table_names():
            self._table(PLAYLISTS).create(
                {
                    TITLE: str,
                    SMART: int,
                    SORTING: str,
                    INCLUDE_PODCAST_IDS: str,
                },
                pk=TITLE,
            )
        if CHAPTERS not in self.db.table_names():
            self._table(CHAPTERS).create(
                {
                    ENCLOSURE_URL: str,
                    GUID: str,
                    SOURCE: str,
                    TIME: int,
                    CONTENT: str,
                    URL: str,
                    IMAGE: str,
                },
                foreign_keys=[
                    (ENCLOSURE_URL, EPISODES, ENCLOSURE_URL),
                ],
            )
            self._table(CHAPTERS).enable_fts(
                [CONTENT],
                create_triggers=True,
            )
            self._table(CHAPTERS).create_index([ENCLOSURE_URL, GUID, SOURCE])

        # Create episode_downloads table for tracking downloaded episodes
        if "episode_downloads" not in self.db.table_names():
            self._table("episode_downloads").create(
                {
                    "media_path": str,
                    "podcast_title": str,
                    "episode_filename": str,
                    "file_size": int,
                    "modified_time": str,
                    "discovered_time": str,
                    "last_verified_time": str,
                    "metadata_json": str,
                    "episode_title": str,
                    "episode_description": str,
                    "episode_summary": str,
                    "episode_shownotes": str,
                    "episode_url": str,
                    "publication_date": str,
                    "duration": int,
                    "metadata_exists": int,
                    "media_exists": int,
                },
                pk="media_path",
            )
            # Enable FTS on text fields
            self._table("episode_downloads").enable_fts(
                [
                    "episode_title",
                    "episode_description",
                    "episode_summary",
                    "episode_shownotes",
                    "podcast_title",
                ],
                create_triggers=True,
            )
            # Create indexes for common queries
            self._table("episode_downloads").create_index(["podcast_title"])
            self._table("episode_downloads").create_index(
                ["publication_date"],
                if_not_exists=True,
            )
            self._table("episode_downloads").create_index(
                ["modified_time"],
                if_not_exists=True,
            )

        # Create transcription tables for tracking transcribed episodes
        if "transcriptions" not in self.db.table_names():
            self._table("transcriptions").create(
                {
                    "transcription_id": int,
                    "audio_content_hash": str,
                    "media_path": str,
                    "file_size": int,
                    "transcription_path": str,
                    "episode_url": str,
                    "podcast_title": str,
                    "episode_title": str,
                    "backend": str,
                    "model_size": str,
                    "language": str,
                    "duration": float,
                    "transcription_time": float,
                    "has_diarization": int,
                    "speaker_count": int,
                    "word_count": int,
                    "created_time": str,
                    "updated_time": str,
                    "metadata_json": str,
                },
                pk="transcription_id",
            )
            # Create unique index on content hash to prevent duplicate transcriptions
            self._table("transcriptions").create_index(
                ["audio_content_hash"],
                unique=True,
                if_not_exists=True,
            )
            # Create index on media_path for lookups by file location
            self._table("transcriptions").create_index(
                ["media_path"],
                if_not_exists=True,
            )
            # Create index on episode_url for linking to episode metadata
            self._table("transcriptions").create_index(
                ["episode_url"],
                if_not_exists=True,
            )

        # Create transcription_segments table for storing individual segments
        if "transcription_segments" not in self.db.table_names():
            self._table("transcription_segments").create(
                {
                    "transcription_id": int,
                    "segment_index": int,
                    "start_time": float,
                    "end_time": float,
                    "text": str,
                    "speaker": str,
                },
                foreign_keys=[
                    ("transcription_id", "transcriptions", "transcription_id"),
                ],
            )
            # Create composite index for efficient segment lookups
            self._table("transcription_segments").create_index(
                ["transcription_id", "segment_index"],
                if_not_exists=True,
            )
            # Enable full-text search on segment text
            self._table("transcription_segments").enable_fts(
                ["text"],
                create_triggers=True,
            )

        self.db.create_view(
            "episodes_played",
            (
                "SELECT "
                f"{EPISODES}.{TITLE}, {FEEDS}.{TITLE} as feed, played, progress, "
                f"CASE WHEN {USER_REC_DATE} IS NOT NULL THEN 1 ELSE 0 END AS starred, "
                f"{USER_UPDATED_DATE}, {EPISODES}.{URL}, {ENCLOSURE_URL} "
                f"FROM {EPISODES} "
                f"LEFT JOIN {FEEDS} ON {EPISODES}.{FEED_ID} = {FEEDS}.{OVERCAST_ID} "
                f"WHERE played=1 OR progress>300 ORDER BY {USER_UPDATED_DATE} DESC"
            ),
            ignore=True,
        )
        self.db.create_view(
            "episodes_deleted",
            (
                "SELECT "
                f"{EPISODES}.{TITLE}, {FEEDS}.{TITLE} as feed, played, progress, "
                f"{USER_UPDATED_DATE}, {EPISODES}.{URL}, {ENCLOSURE_URL} "
                f"FROM {EPISODES} "
                f"LEFT JOIN {FEEDS} ON {EPISODES}.{FEED_ID} = {FEEDS}.{OVERCAST_ID} "
                f"WHERE userDeleted=1 AND played=0 ORDER BY {USER_UPDATED_DATE} DESC"
            ),
            ignore=True,
        )
        self.db.create_view(
            "episodes_starred",
            (
                "SELECT "
                f"{EPISODES}.{TITLE}, {FEEDS}.{TITLE} as feed, played, progress, "
                f"{USER_REC_DATE}, {EPISODES}.{URL}, {ENCLOSURE_URL} "
                f"FROM {EPISODES} "
                f"LEFT JOIN {FEEDS} ON {EPISODES}.{FEED_ID} = {FEEDS}.{OVERCAST_ID} "
                f"WHERE {USER_REC_DATE} IS NOT NULL ORDER BY {USER_UPDATED_DATE} DESC"
            ),
            ignore=True,
        )

    def get_schema_info(self) -> dict[str, list[str]]:
        """Get information about database schema objects for display.
        
        Returns:
            Dictionary with keys 'tables', 'views', 'indices', 'triggers'
        """
        conn = self._connection()
        
        # Get tables (excluding sqlite internal tables and FTS tables)
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' "
                "ORDER BY name"
            ).fetchall()
        ]
        
        # Get views
        views = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' "
                "ORDER BY name"
            ).fetchall()
        ]
        
        # Get indices (excluding auto-generated ones)
        indices = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        ]
        
        # Get triggers
        triggers = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "ORDER BY name"
            ).fetchall()
        ]
        
        # Get FTS tables
        fts_tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name LIKE '%_fts%' "
                "ORDER BY name"
            ).fetchall()
        ]
        
        return {
            "tables": tables,
            "views": views,
            "indices": indices,
            "triggers": triggers,
            "fts_tables": fts_tables,
        }

    def reset_schema(self) -> None:
        """Drop all tables, views, indices and recreate the schema.
        
        WARNING: This is a destructive operation that deletes all data.
        """
        conn = self._connection()
        
        # Disable foreign keys temporarily
        conn.execute("PRAGMA foreign_keys = OFF")
        
        # Get all schema objects
        schema_info = self.get_schema_info()
        
        # Drop triggers first (they depend on tables)
        for trigger in schema_info["triggers"]:
            conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        
        # Drop views (they depend on tables)
        for view in schema_info["views"]:
            conn.execute(f"DROP VIEW IF EXISTS {view}")
        
        # Drop indices (some are associated with FTS)
        for index in schema_info["indices"]:
            conn.execute(f"DROP INDEX IF EXISTS {index}")
        
        # Drop FTS tables
        for fts_table in schema_info["fts_tables"]:
            conn.execute(f"DROP TABLE IF EXISTS {fts_table}")
        
        # Drop regular tables
        for table in schema_info["tables"]:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        
        conn.commit()
        
        # Re-enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        
        # Recreate schema
        self._prepare_db()

    def save_feed_and_episodes(
        self,
        feed: dict,
        episodes: list[dict],
    ) -> None:
        """Upsert feed and episodes into database."""
        self._table(FEEDS).upsert(feed, pk=OVERCAST_ID)
        self._table(EPISODES).upsert_all(episodes, pk=OVERCAST_ID)

    def save_extended_feed_and_episodes(
        self,
        feed: dict,
        episodes: list[dict],
    ) -> None:
        """Upsert feed info (with new columns) and insert episodes (ignore existing)."""
        self._table(FEEDS_EXTENDED).upsert(feed, pk=XML_URL, alter=True)
        self._table(EPISODES_EXTENDED).insert_all(
            episodes,
            pk=ENCLOSURE_URL,
            ignore=True,
            alter=True,
        )

    def mark_feed_removed_if_missing(
        self,
        ingested_feed_ids: set[int],
    ) -> None:
        """Set feeds as removed at now if they are not in the ingested feed ids."""
        stored_feed_ids = self.db.execute(
            f"SELECT {OVERCAST_ID} FROM {FEEDS} WHERE dateRemoveDetected IS null",
        ).fetchall()
        stored_feed_ids = {x[0] for x in stored_feed_ids}
        deleted_ids = stored_feed_ids - ingested_feed_ids

        now = datetime.datetime.now(tz=datetime.UTC).isoformat()
        for feed_id in deleted_ids:
            self._table(FEEDS).update(feed_id, {"dateRemoveDetected": now})

    def get_feeds_to_extend(self) -> list[tuple[str, str]]:
        """Find feeds with episodes not represented in episodes_extended."""
        return self.db.execute(
            f"SELECT {FEEDS}.{TITLE}, {FEEDS}.{XML_URL} "
            f"FROM {EPISODES} "
            f"LEFT JOIN {EPISODES_EXTENDED} "
            f"ON {EPISODES}.{ENCLOSURE_URL} = {EPISODES_EXTENDED}.{ENCLOSURE_URL} "
            f"LEFT JOIN {FEEDS} "
            f"ON {EPISODES}.{FEED_ID} = {FEEDS}.{OVERCAST_ID} "
            f"LEFT JOIN {FEEDS_EXTENDED} "
            f"ON {FEEDS}.{XML_URL} = {FEEDS_EXTENDED}.{XML_URL} "
            f"WHERE {EPISODES_EXTENDED}.{ENCLOSURE_URL} IS NULL "
            f"AND ({FEEDS_EXTENDED}.{LAST_UPDATED} IS NULL "
            f"OR {FEEDS_EXTENDED}.{LAST_UPDATED} < {EPISODES}.{PUB_DATE}) "
            f"GROUP BY {FEED_ID};",
        ).fetchall()

    def save_playlist(self, playlist: dict) -> None:
        """Upsert playlist into database."""
        self._table(PLAYLISTS).upsert(playlist, pk=TITLE)

    def ensure_transcript_columns(self) -> bool:
        """Ensure transcript columns exist in database.

        Returns bool indicating if columns were added.
        """
        columns_added = False
        try:
            self.db.execute(f"SELECT {TRANSCRIPT_URL} FROM {EPISODES_EXTENDED} LIMIT 1")
        except sqlite3.OperationalError:
            self._table(EPISODES_EXTENDED).add_column(TRANSCRIPT_DL_PATH, str)
            columns_added = True
        try:
            self.db.execute(
                f"SELECT {TRANSCRIPT_DL_PATH} FROM {EPISODES_EXTENDED} LIMIT 1",
            )
        except sqlite3.OperationalError:
            self._table(EPISODES_EXTENDED).add_column(TRANSCRIPT_DL_PATH, str)
            columns_added = True
        return columns_added

    # TRANSCRIPTS

    def transcripts_to_download(
        self,
        *,
        starred_only: bool,
    ) -> Iterable[tuple[str, str, str, str, str]]:
        """Find episodes with transcripts to download.

        Yields (title, url, mime_type, enclosure_url, feed_title)
        """
        select = (
            f"SELECT {EPISODES_EXTENDED}.{TITLE}, {TRANSCRIPT_URL}, "
            f"{TRANSCRIPT_TYPE}, {EPISODES_EXTENDED}.{ENCLOSURE_URL}, "
            f"{FEEDS_EXTENDED}.{TITLE} FROM {EPISODES_EXTENDED} "
        )
        where = f"WHERE {TRANSCRIPT_DL_PATH} IS NULL AND {TRANSCRIPT_URL} IS NOT NULL"
        order = f"ORDER BY {FEEDS_EXTENDED}.{TITLE} ASC"
        query = (
            (
                f"{select} LEFT JOIN {FEEDS_EXTENDED} "
                f"ON {EPISODES_EXTENDED}.{FEED_XML_URL} = {FEEDS_EXTENDED}.{XML_URL} "
                f"{where} {order}"
            )
            if not starred_only
            else (
                f"{select} "
                f"LEFT JOIN {EPISODES} "
                f"ON {EPISODES_EXTENDED}.{ENCLOSURE_URL} = {EPISODES}.{ENCLOSURE_URL} "
                f"LEFT JOIN {FEEDS_EXTENDED} "
                f"ON {EPISODES_EXTENDED}.{FEED_XML_URL} = {FEEDS_EXTENDED}.{XML_URL} "
                f"{where} AND {USER_REC_DATE} IS NOT NULL {order}"
            )
        )

        yield from self.db.execute(query)

    def update_transcript_download_paths(
        self,
        enclosure: str,
        transcript_path: str,
    ) -> None:
        """Update episode with transcript download path."""
        self._table(EPISODES_EXTENDED).update(
            enclosure,
            {TRANSCRIPT_DL_PATH: transcript_path},
        )

    # CHAPTERS
    def insert_chapters(
        self,
        chapters: list[tuple[str, str, str, int, str, str | None, str | None]],
    ) -> None:
        """Insert chapters into the chapters DB table."""
        conn = self._connection()
        conn.executemany(
            f"INSERT INTO {CHAPTERS} "
            f"({ENCLOSURE_URL}, {GUID}, {SOURCE}, {TIME}, {CONTENT}, {URL}, {IMAGE}) "
            "VALUES (?, ?, ?, ?, ?, ?, ?);",
            chapters,
        )
        conn.commit()

    def get_description_no_chapters(self) -> Iterable[tuple[str, str, str]]:
        """Find episodes with no chapters."""
        yield from self.db.execute(
            f"SELECT {EPISODES_EXTENDED}.{ENCLOSURE_URL}, {EPISODES_EXTENDED}.{GUID}, "
            f"{DESCRIPTION} "
            f"FROM {EPISODES_EXTENDED} "
            f"LEFT JOIN {CHAPTERS} "
            f"ON {EPISODES_EXTENDED}.{ENCLOSURE_URL} = {CHAPTERS}.{ENCLOSURE_URL} "
            f"WHERE {CHAPTERS}.{ENCLOSURE_URL} IS NULL "
            f"AND {DESCRIPTION} IS NOT NULL;",
        )

    def get_no_pci_chapters(self) -> Iterable[tuple[str, str, str, str]]:
        """Find episodes with no PCI type chapters."""
        yield from self.db.execute(
            f"SELECT {EPISODES_EXTENDED}.{ENCLOSURE_URL}, {EPISODES_EXTENDED}.{GUID}, "
            f'{EPISODES_EXTENDED}.{TITLE}, "podcast:chapters:url"'
            f"FROM {EPISODES_EXTENDED} "
            f"LEFT JOIN {CHAPTERS} "
            f"ON {EPISODES_EXTENDED}.{ENCLOSURE_URL} = {CHAPTERS}.{ENCLOSURE_URL} "
            f"WHERE {CHAPTERS}.{ENCLOSURE_URL} IS NULL "
            'AND "podcast:chapters:url" IS NOT NULL '
            f"AND ({CHAPTERS}.{SOURCE} IS NULL OR {CHAPTERS}.{SOURCE} != 'pci');",
        )

    def get_no_psc_chapters(self) -> Iterable[tuple[str, str, str]]:
        """Find episodes with no PCI type chapters."""
        yield from self.db.execute(
            f"SELECT {EPISODES_EXTENDED}.{ENCLOSURE_URL}, {EPISODES_EXTENDED}.{GUID}, "
            f"{FEEDS_EXTENDED}.{TITLE} "
            f"FROM {EPISODES_EXTENDED} "
            f"LEFT JOIN {CHAPTERS} "
            f"ON {EPISODES_EXTENDED}.{ENCLOSURE_URL} = {CHAPTERS}.{ENCLOSURE_URL} "
            f"LEFT JOIN {FEEDS_EXTENDED} "
            f"ON {EPISODES_EXTENDED}.{FEED_XML_URL} = {FEEDS_EXTENDED}.{XML_URL} "
            f"WHERE {CHAPTERS}.{ENCLOSURE_URL} IS NULL "
            'AND "psc:chapters:version" IS NOT NULL '
            f"AND ({CHAPTERS}.{SOURCE} IS NULL OR {CHAPTERS}.{SOURCE} != 'psc');",
        )

    def get_feed_titles(self, *, subscribed_only: bool = True) -> list[str]:
        """Retrieve a list of feed titles."""
        query = f"SELECT {TITLE} FROM {FEEDS}"
        if subscribed_only:
            query += " WHERE subscribed = 1 AND dateRemoveDetected IS NULL"
        query += f" ORDER BY {TITLE} ASC"
        results = self.db.execute(query).fetchall()
        return [row[0] for row in results]

    def get_feed_data(self, *, subscribed_only: bool = True) -> list[dict]:
        """Retrieve detailed feed data as a list of dictionaries.

        Args:
            subscribed_only: If True, only return subscribed feeds.

        Returns:
            List of feed data dictionaries.

        """
        query = f"""
            SELECT
                {OVERCAST_ID},
                {TITLE},
                subscribed,
                overcastAddedDate,
                notifications,
                {XML_URL},
                htmlUrl,
                dateRemoveDetected
            FROM {FEEDS}
        """

        if subscribed_only:
            query += " WHERE subscribed = 1 AND dateRemoveDetected IS NULL"

        query += f" ORDER BY {TITLE} ASC"

        results = self.db.execute(query).fetchall()

        feed_data = []
        for row in results:
            feed_dict = {
                "overcastId": row[0],
                "title": row[1],
                "subscribed": bool(row[2]),
                "overcastAddedDate": row[3],
                "notifications": bool(row[4]),
                "xmlUrl": row[5],
                "htmlUrl": row[6],
                "dateRemoveDetected": row[7],
            }
            feed_data.append(feed_dict)

        return feed_data

    def get_episodes_by_feed_titles(
        self,
        feed_titles: list[str],
        *,
        all_episodes: bool = False,
    ) -> list[dict[str, str]]:
        """Retrieve episodes filtered by feed titles."""
        if not feed_titles:
            return []

        placeholders = ", ".join("?" * len(feed_titles))
        where_clauses = [f"{FEEDS}.{TITLE} IN ({placeholders})"]
        if not all_episodes:
            where_clauses.append(f"{EPISODES}.played = 1")

        query = f"""
            SELECT
                {EPISODES}.{TITLE} as episode_title,
                {FEEDS}.{TITLE} as feed_title,
                {EPISODES}.played,
                {EPISODES}.progress,
                {EPISODES}.{USER_UPDATED_DATE},
                {EPISODES}.{USER_REC_DATE},
                {EPISODES}.{PUB_DATE},
                {EPISODES}.{URL} as episode_url,
                {EPISODES}.{ENCLOSURE_URL}
            FROM {EPISODES}
            LEFT JOIN {FEEDS} ON {EPISODES}.{FEED_ID} = {FEEDS}.{OVERCAST_ID}
            WHERE {" AND ".join(where_clauses)}
            ORDER BY {FEEDS}.{TITLE}, {EPISODES}.{PUB_DATE} DESC,
                     {EPISODES}.{USER_UPDATED_DATE} DESC
        """

        results = self.db.execute(query, feed_titles).fetchall()
        columns = [
            "episode_title",
            "feed_title",
            "played",
            "progress",
            "userUpdatedDate",
            "userRecommendedDate",
            "pubDate",
            "episode_url",
            "enclosureUrl",
        ]

        return [{columns[i]: result[i] for i in range(len(columns))} for result in results]

    def get_recently_played(self) -> list[dict[str, str]]:
        """Retrieve a list of recently played episodes with metadata."""
        conn = self._connection()
        self.db.execute(
            f"UPDATE {EPISODES} "
            f"SET {ENCLOSURE_URL} = "
            f"substr({ENCLOSURE_URL}, 1, instr({ENCLOSURE_URL}, '?') - 1) "
            f"WHERE {ENCLOSURE_URL} LIKE '%?%'",
        )
        conn.commit()

        self.db.execute(
            f"""
            DELETE FROM {EPISODES_EXTENDED} WHERE rowid IN (
                SELECT t1.rowid
                FROM {EPISODES_EXTENDED} t1
                JOIN (
                    SELECT
                        substr({ENCLOSURE_URL}, 1, instr({ENCLOSURE_URL}, '?') - 1)
                        AS base_url,
                        MIN(rowid) AS min_rowid
                    FROM {EPISODES_EXTENDED}
                    WHERE {ENCLOSURE_URL} LIKE '%?%'
                    GROUP BY base_url
                ) t2 ON
                substr(t1.{ENCLOSURE_URL}, 1, instr(t1.{ENCLOSURE_URL}, '?') - 1)
                = t2.base_url
                WHERE  t1.rowid > t2.min_rowid
            )
            """,
        )
        conn.commit()

        self.db.execute(
            f"UPDATE OR IGNORE {EPISODES_EXTENDED} "
            f"SET {ENCLOSURE_URL} = "
            f"substr({ENCLOSURE_URL}, 1, instr({ENCLOSURE_URL}, '?') - 1) "
            f"WHERE {ENCLOSURE_URL} LIKE '%?%'",
        )
        conn.commit()

        fields = [
            f"{EPISODES}.{TITLE}",
            f"{EPISODES}.{URL}",
            f"{FEEDS_EXTENDED}.{TITLE} as feed_title",
            f"{FEEDS_EXTENDED}.'itunes:image:href' as image_",
            f"{FEEDS_EXTENDED}.link as link_",
            f"coalesce({EPISODES_EXTENDED}.description, 'No description') as description",
            f"{EPISODES_EXTENDED}.pubDate as pubDate",
            f"{EPISODES_EXTENDED}.'itunes:image:href' as 'images.'",
            f"{EPISODES_EXTENDED}.link as 'links.'",
            f"{USER_UPDATED_DATE}",
            "starred",
        ]
        query = (
            "SELECT "
            + ", ".join(fields[:-1])
            + (
                f", CASE WHEN {USER_REC_DATE} IS NOT NULL THEN 1 ELSE 0 END AS starred "
                f"FROM {EPISODES} "
                f"JOIN {EPISODES_EXTENDED} ON "
                f"{EPISODES}.{ENCLOSURE_URL} = {EPISODES_EXTENDED}.{ENCLOSURE_URL} "
                f"JOIN {FEEDS_EXTENDED} "
                f"ON {EPISODES_EXTENDED}.{FEED_XML_URL} = {FEEDS_EXTENDED}.{XML_URL} "
                f"WHERE played=1 OR progress>300 ORDER BY {USER_UPDATED_DATE} DESC "
                f"LIMIT 100"
            )
        )

        results = self.db.execute(query).fetchall()
        return [
            {
                fields[i].split(" ")[-1].replace("s.", "_").replace("'", ""): v
                for (i, v) in enumerate(result)
                if v is not None
            }
            for result in results
        ]

    # EPISODE DOWNLOADS

    def ensure_episode_downloads_table(self) -> None:
        """Create episode_downloads table and indexes if not exists.

        This method is idempotent and safe to call multiple times.
        The table creation is handled in _prepare_db(), so this method
        simply verifies the table exists.
        """
        # Table creation happens in _prepare_db()
        # This method exists for explicit initialization in CLI commands
        if "episode_downloads" not in self.db.table_names():
            # Re-run prepare_db to create the table
            self._prepare_db()

    def upsert_episode_download(self, episode_info: dict) -> None:
        """Insert or update episode download record.

        Args:
            episode_info: Dictionary containing episode metadata fields.
                Required fields: media_path
                Optional fields: podcast_title, episode_filename, file_size,
                    modified_time, discovered_time, last_verified_time,
                    metadata_json, episode_title, episode_description,
                    episode_summary, episode_shownotes, episode_url,
                    publication_date, duration, metadata_exists, media_exists
        """
        self._table("episode_downloads").upsert(episode_info, pk="media_path")

    def upsert_episode_downloads_batch(self, episodes: list[dict]) -> None:
        """Batch insert/update episode downloads.

        Args:
            episodes: List of episode info dictionaries.
                Each dict should have the same structure as upsert_episode_download.
        """
        if not episodes:
            return
        self._table("episode_downloads").upsert_all(episodes, pk="media_path")

    def get_episode_downloads(
        self,
        podcast_title: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Query episode downloads with optional filters.

        Args:
            podcast_title: Optional filter by podcast title.
            limit: Optional limit on number of results.

        Returns:
            List of episode download records as dictionaries.
        """
        query = "SELECT * FROM episode_downloads"
        params = []

        if podcast_title:
            query += " WHERE podcast_title = ?"
            params.append(podcast_title)

        query += " ORDER BY publication_date DESC"

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute(query, params).fetchall()

        # Get column names
        cursor = self.db.execute("SELECT * FROM episode_downloads LIMIT 0")
        columns = [description[0] for description in cursor.description]

        # Convert to list of dicts
        return [dict(zip(columns, row)) for row in results]

    def mark_missing_episodes(self, existing_paths: set[str]) -> int:
        """Mark episodes as media_exists=0 if not in existing_paths.

        Args:
            existing_paths: Set of media file paths that currently exist on disk.

        Returns:
            Number of episodes marked as missing.
        """
        # Get all media paths from database
        all_paths = self.db.execute(
            "SELECT media_path FROM episode_downloads WHERE media_exists = 1",
        ).fetchall()

        missing_count = 0
        for (path,) in all_paths:
            if path not in existing_paths:
                self._table("episode_downloads").update(
                    path,
                    {"media_exists": 0},
                )
                missing_count += 1

        return missing_count

    def search_episode_downloads(self, query: str) -> list[dict]:
        """Full-text search across episode titles/descriptions.

        Args:
            query: Search query string.

        Returns:
            List of matching episode download records.
        """
        # Use FTS table for search
        sql_query = """
            SELECT episode_downloads.*
            FROM episode_downloads
            JOIN episode_downloads_fts
            ON episode_downloads.rowid = episode_downloads_fts.rowid
            WHERE episode_downloads_fts MATCH ?
            ORDER BY rank
        """

        results = self.db.execute(sql_query, [query]).fetchall()

        # Get column names
        cursor = self.db.execute("SELECT * FROM episode_downloads LIMIT 0")
        columns = [description[0] for description in cursor.description]

        # Convert to list of dicts
        return [dict(zip(columns, row)) for row in results]

    # TRANSCRIPTIONS

    def upsert_transcription(
        self,
        audio_content_hash: str,
        media_path: str,
        file_size: int,
        transcription_path: str | None,
        episode_url: str | None,
        podcast_title: str,
        episode_title: str,
        backend: str,
        model_size: str,
        language: str,
        duration: float,
        transcription_time: float,
        has_diarization: bool,
        speaker_count: int,
        word_count: int,
        segments: list,
    ) -> int:
        """Insert or update transcription record with segments.

        Args:
            audio_content_hash: SHA256 hash of audio content
            media_path: Path to audio file
            file_size: File size in bytes
            transcription_path: Path to transcription output file
            episode_url: Optional episode URL for linking
            podcast_title: Podcast title
            episode_title: Episode title
            backend: Backend used (mlx-whisper, faster-whisper, etc.)
            model_size: Model size (tiny, base, small, medium, large)
            language: Language code (e.g., "en")
            duration: Audio duration in seconds
            transcription_time: Time taken to transcribe
            has_diarization: Whether diarization was applied
            speaker_count: Number of speakers detected
            word_count: Total word count
            segments: List of TranscriptionSegment objects

        Returns:
            Transcription ID
        """
        import json

        now = datetime.datetime.now(tz=datetime.UTC).isoformat()

        # Prepare metadata
        metadata = {
            "backend": backend,
            "model_size": model_size,
            "transcription_time": transcription_time,
        }

        # Prepare transcription record
        transcription_record = {
            "audio_content_hash": audio_content_hash,
            "media_path": media_path,
            "file_size": file_size,
            "transcription_path": transcription_path,
            "episode_url": episode_url,
            "podcast_title": podcast_title,
            "episode_title": episode_title,
            "backend": backend,
            "model_size": model_size,
            "language": language,
            "duration": duration,
            "transcription_time": transcription_time,
            "has_diarization": 1 if has_diarization else 0,
            "speaker_count": speaker_count,
            "word_count": word_count,
            "created_time": now,
            "updated_time": now,
            "metadata_json": json.dumps(metadata),
        }

        # Check if transcription exists
        existing = list(
            self._table("transcriptions").rows_where(
                "audio_content_hash = ?",
                [audio_content_hash],
                limit=1,
            )
        )

        transcription_id: int
        if existing:
            # Update existing record
            transcription_id = existing[0]["transcription_id"]
            transcription_record["transcription_id"] = transcription_id
            transcription_record["created_time"] = existing[0][
                "created_time"
            ]  # Keep original
            self._table("transcriptions").update(
                transcription_id,
                transcription_record,
            )
        else:
            # Insert new record
            try:
                self._table("transcriptions").insert(transcription_record)
                # Get the last inserted row ID using SQL
                transcription_id = self.db.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]
            except Exception as e:
                # Provide detailed error information
                raise RuntimeError(
                    f"Failed to insert transcription record for {media_path}. "
                    f"Audio hash: {audio_content_hash}. "
                    f"Error: {type(e).__name__}: {e}"
                ) from e

        # Save segments
        self._upsert_transcription_segments(transcription_id, segments)

        return transcription_id

    def _upsert_transcription_segments(
        self,
        transcription_id: int,
        segments: list,
    ) -> None:
        """Insert or update transcription segments.

        Args:
            transcription_id: ID of parent transcription
            segments: List of TranscriptionSegment objects
        """
        # Delete existing segments for this transcription
        self.db.execute(
            "DELETE FROM transcription_segments WHERE transcription_id = ?",
            [transcription_id],
        )

        # Prepare segment records
        segment_records = []
        for i, segment in enumerate(segments):
            # Handle both dict and TranscriptionSegment object
            if isinstance(segment, dict):
                start = segment["start"]
                end = segment["end"]
                text = segment["text"]
                speaker = segment.get("speaker")
            else:
                start = segment.start
                end = segment.end
                text = segment.text
                speaker = segment.speaker

            segment_records.append(
                {
                    "transcription_id": transcription_id,
                    "segment_index": i,
                    "start_time": start,
                    "end_time": end,
                    "text": text,
                    "speaker": speaker,
                }
            )

        # Insert all segments
        if segment_records:
            self._table("transcription_segments").insert_all(segment_records)

    def get_transcription_by_hash(
        self,
        audio_hash: str,
    ) -> dict | None:
        """Get transcription by audio content hash.

        Args:
            audio_hash: SHA256 hash of audio content

        Returns:
            Transcription record dict or None if not found
        """
        rows = list(
            self._table("transcriptions").rows_where(
                "audio_content_hash = ?",
                [audio_hash],
                limit=1,
            )
        )
        return dict(rows[0]) if rows else None

    def get_transcription_by_path(
        self,
        media_path: str,
    ) -> dict | None:
        """Get transcription by media file path.

        Args:
            media_path: Path to media file

        Returns:
            Transcription record dict or None if not found
        """
        rows = list(
            self._table("transcriptions").rows_where(
                "media_path = ?",
                [media_path],
                limit=1,
            )
        )
        return dict(rows[0]) if rows else None

    def search_transcriptions(
        self,
        query: str,
        podcast_title: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Full-text search across transcription segments.

        Args:
            query: Search query string
            podcast_title: Optional filter by podcast title
            limit: Optional limit on number of results

        Returns:
            List of matching segments with transcription metadata
        """
        # Build query
        sql_query = """
            SELECT
                transcriptions.transcription_id,
                transcriptions.podcast_title,
                transcriptions.episode_title,
                transcriptions.media_path,
                transcriptions.language,
                transcriptions.duration,
                transcription_segments.segment_index,
                transcription_segments.start_time,
                transcription_segments.end_time,
                transcription_segments.text,
                transcription_segments.speaker
            FROM transcription_segments
            JOIN transcription_segments_fts
                ON transcription_segments.rowid = transcription_segments_fts.rowid
            JOIN transcriptions
                ON transcription_segments.transcription_id = transcriptions.transcription_id
            WHERE transcription_segments_fts MATCH ?
        """

        params = [query]

        if podcast_title:
            sql_query += " AND transcriptions.podcast_title = ?"
            params.append(podcast_title)

        sql_query += " ORDER BY rank"

        if limit:
            sql_query += f" LIMIT {limit}"

        results = self.db.execute(sql_query, params).fetchall()

        # Convert to list of dicts
        columns = [
            "transcription_id",
            "podcast_title",
            "episode_title",
            "media_path",
            "language",
            "duration",
            "segment_index",
            "start_time",
            "end_time",
            "text",
            "speaker",
        ]

        return [dict(zip(columns, row)) for row in results]
