"""Filesystem scanner for discovering downloaded podcast episodes."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from loguru import logger


@dataclass
class EpisodeFileInfo:
    """Represents discovered episode files on disk."""

    media_path: Path
    podcast_title: str
    episode_filename: str
    file_size: int
    modified_time: datetime
    metadata_path: Path | None
    metadata_exists: bool


class EpisodeScanner:
    """Scans episode_downloads directory for media and metadata."""

    def __init__(self, downloads_dir: Path) -> None:
        """Initialize scanner with downloads directory.

        Args:
            downloads_dir: Path to the episode_downloads directory.
        """
        self.downloads_dir = Path(downloads_dir)
        self.supported_extensions = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"}

    def scan(self) -> list[EpisodeFileInfo]:
        """Discover all episode files in downloads directory.

        Walks the downloads directory structure, expecting:
            downloads_dir/
                Podcast Name/
                    episode_file.mp3
                    episode_file.info.json

        Returns:
            List of EpisodeFileInfo objects for discovered episodes.
        """
        episodes = []

        if not self.downloads_dir.exists():
            logger.warning(f"Downloads directory does not exist: {self.downloads_dir}")
            return episodes

        # Walk directory tree - expect depth 2 (podcast/episode)
        for podcast_dir in self.downloads_dir.iterdir():
            if not podcast_dir.is_dir():
                continue

            podcast_title = podcast_dir.name

            # Find media files in podcast directory
            for media_file in podcast_dir.iterdir():
                if not media_file.is_file():
                    continue

                # Check if this is a supported media file
                if media_file.suffix.lower() not in self.supported_extensions:
                    continue

                # Look for corresponding .info.json file
                # Try both .info.json and .json extensions
                metadata_path = media_file.with_suffix(media_file.suffix + ".info.json")
                if not metadata_path.exists():
                    # Try alternate naming: remove extension and add .info.json
                    metadata_path = media_file.with_suffix(".info.json")

                metadata_exists = metadata_path.exists() if metadata_path else False

                # Get file stats
                stats = media_file.stat()
                file_size = stats.st_size
                modified_time = datetime.fromtimestamp(stats.st_mtime)

                episode_info = EpisodeFileInfo(
                    media_path=media_file,
                    podcast_title=podcast_title,
                    episode_filename=media_file.name,
                    file_size=file_size,
                    modified_time=modified_time,
                    metadata_path=metadata_path if metadata_exists else None,
                    metadata_exists=metadata_exists,
                )

                episodes.append(episode_info)
                logger.debug(
                    f"Found episode: {podcast_title} - {media_file.name} "
                    f"(metadata: {metadata_exists})",
                )

        logger.info(f"Scanned {len(episodes)} episodes from {self.downloads_dir}")
        return episodes

    def read_metadata(self, info_json_path: Path) -> dict:
        """Parse .info.json file and return metadata.

        Args:
            info_json_path: Path to the .info.json file.

        Returns:
            Dictionary containing metadata from JSON file.
            Returns empty dict if file cannot be read or parsed.
        """
        try:
            with info_json_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
                logger.debug(f"Read metadata from {info_json_path}")
                return metadata
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {info_json_path}: {e}")
            return {}
        except OSError as e:
            logger.warning(f"Failed to read file {info_json_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error reading {info_json_path}: {e}")
            return {}

    def extract_fields(self, metadata: dict) -> dict:
        """Extract key fields from metadata for database columns.

        Maps various possible JSON field names to standardized database columns.
        Handles podcast-archiver and yt-dlp metadata formats.

        Args:
            metadata: Dictionary containing episode metadata from .info.json.

        Returns:
            Dictionary with extracted fields:
                - episode_title: str | None
                - episode_description: str | None
                - episode_summary: str | None (short description)
                - episode_shownotes: str | None (full description/notes)
                - episode_url: str | None
                - publication_date: str | None (ISO8601 format)
                - duration: int | None (seconds)
        """
        extracted = {}

        # Title - try multiple field names
        title_fields = ["title", "episode", "episode_title", "fulltitle"]
        extracted["episode_title"] = self._find_first_value(metadata, title_fields)

        # Summary - short description (usually < 200 chars)
        summary_fields = ["summary", "subtitle", "itunes_summary", "short_description"]
        extracted["episode_summary"] = self._find_first_value(metadata, summary_fields)

        # Shownotes - full description with HTML/formatting
        shownotes_fields = [
            "description",
            "long_description",
            "shownotes",
            "content",
            "itunes_description",
        ]
        extracted["episode_shownotes"] = self._find_first_value(
            metadata,
            shownotes_fields,
        )

        # Description - medium-length description
        # Use shownotes if no dedicated description field
        description_fields = ["description", "subtitle"]
        extracted["episode_description"] = self._find_first_value(
            metadata,
            description_fields,
        )
        if not extracted["episode_description"]:
            extracted["episode_description"] = extracted["episode_shownotes"]

        # URL
        url_fields = ["url", "webpage_url", "original_url", "link"]
        extracted["episode_url"] = self._find_first_value(metadata, url_fields)

        # Publication date - normalize to ISO8601
        date_fields = ["upload_date", "release_date", "pubDate", "pub_date", "published"]
        raw_date = self._find_first_value(metadata, date_fields)
        extracted["publication_date"] = self._normalize_date(raw_date)

        # Duration in seconds
        duration = metadata.get("duration")
        if duration is not None:
            try:
                extracted["duration"] = int(duration)
            except (ValueError, TypeError):
                logger.debug(f"Could not convert duration to int: {duration}")
                extracted["duration"] = None
        else:
            extracted["duration"] = None

        # Normalize empty strings to None
        for key, value in extracted.items():
            if value == "":
                extracted[key] = None

        return extracted

    def _find_first_value(self, metadata: dict, field_names: list[str]) -> str | None:
        """Find first non-empty value for any of the given field names.

        Args:
            metadata: Metadata dictionary to search.
            field_names: List of field names to try in order.

        Returns:
            First non-empty string value found, or None.
        """
        for field_name in field_names:
            value = metadata.get(field_name)
            if value and isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _normalize_date(self, date_value: str | int | None) -> str | None:
        """Normalize date value to ISO8601 format.

        Handles various date formats:
        - ISO8601 strings (already formatted)
        - YYYYMMDD format (common in yt-dlp)
        - Unix timestamps
        - RFC 2822 format

        Args:
            date_value: Date value in various possible formats.

        Returns:
            ISO8601 formatted date string, or None if parsing fails.
        """
        if not date_value:
            return None

        # If already a string in ISO format, return as-is
        if isinstance(date_value, str):
            # Handle YYYYMMDD format (e.g., "20231215")
            if len(date_value) == 8 and date_value.isdigit():
                try:
                    dt = datetime.strptime(date_value, "%Y%m%d")
                    return dt.isoformat()
                except ValueError:
                    pass

            # Try parsing ISO8601 format
            try:
                # Just validate and return
                datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                return date_value
            except ValueError:
                pass

            # Try RFC 2822 format (common in RSS feeds)
            try:
                from email.utils import parsedate_to_datetime

                dt = parsedate_to_datetime(date_value)
                return dt.isoformat()
            except (ValueError, TypeError):
                pass

        # Handle Unix timestamp (int or string)
        if isinstance(date_value, int) or (
            isinstance(date_value, str) and date_value.isdigit()
        ):
            try:
                timestamp = int(date_value)
                dt = datetime.fromtimestamp(timestamp)
                return dt.isoformat()
            except (ValueError, OSError):
                pass

        logger.debug(f"Could not normalize date: {date_value}")
        return None
