"""Utility functions for transcription module."""

import hashlib
import re
from pathlib import Path
from typing import Optional

from retrocast.datastore import Datastore


def compute_audio_hash(audio_path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of audio file for content-based deduplication.

    This hash is used to identify duplicate audio content even if files are
    moved, renamed, or downloaded multiple times.

    Args:
        audio_path: Path to audio file
        chunk_size: Read chunk size in bytes (default 8KB)

    Returns:
        Hexadecimal SHA256 hash string

    Raises:
        FileNotFoundError: If audio file doesn't exist
        IOError: If file cannot be read
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    sha256_hash = hashlib.sha256()

    with open(audio_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def check_transcription_exists(
    datastore: Datastore, audio_hash: str
) -> tuple[bool, Optional[dict]]:
    """Check if transcription already exists for given audio content.

    Args:
        datastore: Datastore instance
        audio_hash: SHA256 hash of audio content

    Returns:
        Tuple of (exists: bool, transcription_record: dict | None)
    """
    table = datastore.db["transcriptions"]
    try:
        # Use rows_where to find by audio_content_hash
        rows = list(table.rows_where("audio_content_hash = ?", [audio_hash], limit=1))
        if rows:
            return (True, dict(rows[0]))
        return (False, None)
    except Exception:
        return (False, None)


def sanitize_for_path(text: str, max_length: int = 200) -> str:
    """Sanitize text for use in filesystem paths.

    Removes or replaces characters that are invalid in filenames on
    common filesystems (Windows, macOS, Linux).

    Args:
        text: Text to sanitize
        max_length: Maximum length of resulting string (default 200)

    Returns:
        Sanitized string safe for filesystem paths
    """
    # Replace path separators and other problematic characters
    sanitized = text.replace("/", "-").replace("\\", "-")

    # Remove or replace other invalid characters
    # Windows forbids: < > : " / \ | ? *
    # Also remove control characters
    sanitized = re.sub(r'[<>:"|?*\x00-\x1f]', "", sanitized)

    # Replace multiple spaces/hyphens with single ones
    sanitized = re.sub(r"[ ]+", " ", sanitized)
    sanitized = re.sub(r"[-]+", "-", sanitized)

    # Trim whitespace and periods (Windows doesn't like trailing periods)
    sanitized = sanitized.strip(". \t\n\r")

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip(". ")

    # If empty after sanitization, use a default
    if not sanitized:
        sanitized = "untitled"

    return sanitized


def get_output_path(
    output_dir: Path,
    podcast_title: str,
    episode_title: str,
    format_ext: str,
) -> Path:
    """Determine output path for transcription file.

    Creates a directory structure: output_dir/Podcast Name/Episode Title.ext

    Args:
        output_dir: Base output directory
        podcast_title: Podcast title (used for subdirectory)
        episode_title: Episode title (used for filename)
        format_ext: File extension (e.g., "json", "txt", "srt")

    Returns:
        Complete path for transcription output file
    """
    # Sanitize podcast and episode titles
    safe_podcast = sanitize_for_path(podcast_title)
    safe_episode = sanitize_for_path(episode_title)

    # Create podcast directory
    podcast_dir = output_dir / safe_podcast
    podcast_dir.mkdir(parents=True, exist_ok=True)

    # Construct output path
    filename = f"{safe_episode}.{format_ext}"
    return podcast_dir / filename


def get_audio_metadata(audio_path: Path) -> dict:
    """Extract basic metadata from audio file.

    Args:
        audio_path: Path to audio file

    Returns:
        Dictionary with file_size, extension, and other basic metadata
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    stat = audio_path.stat()
    return {
        "file_size": stat.st_size,
        "extension": audio_path.suffix.lower(),
        "filename": audio_path.name,
    }


def format_duration(seconds: float) -> str:
    """Format duration in seconds as HH:MM:SS string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_timestamp(seconds: float, include_hours: bool = True) -> str:
    """Format timestamp for subtitle formats (SRT, VTT).

    Args:
        seconds: Time in seconds
        include_hours: Whether to include hours in format

    Returns:
        Formatted timestamp (e.g., "00:01:23.456")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    if include_hours:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    return f"{minutes:02d}:{secs:06.3f}"
