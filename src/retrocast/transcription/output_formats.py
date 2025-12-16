"""Output format writers for transcription results."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type

from retrocast.transcription.base import TranscriptionResult
from retrocast.transcription.utils import format_timestamp


class FormatWriter(ABC):
    """Abstract base class for transcription output format writers."""

    @property
    @abstractmethod
    def extension(self) -> str:
        """File extension for this format (without dot)."""
        pass

    @abstractmethod
    def write(self, result: TranscriptionResult, output_path: Path) -> None:
        """Write transcription result to file.

        Args:
            result: TranscriptionResult to write
            output_path: Output file path

        Raises:
            IOError: If file cannot be written
        """
        pass


class TXTFormatWriter(FormatWriter):
    """Plain text format writer.

    Writes transcription as plain text with optional timestamps.
    """

    def __init__(self, include_timestamps: bool = True):
        """Initialize TXT writer.

        Args:
            include_timestamps: Whether to include timestamps in output
        """
        self.include_timestamps = include_timestamps

    @property
    def extension(self) -> str:
        return "txt"

    def write(self, result: TranscriptionResult, output_path: Path) -> None:
        """Write transcription as plain text."""
        with open(output_path, "w", encoding="utf-8") as f:
            if self.include_timestamps:
                # Write with timestamps
                for segment in result.segments:
                    timestamp = format_timestamp(segment.start, include_hours=True)
                    speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
                    f.write(f"[{timestamp}] {speaker_prefix}{segment.text}\n")
            else:
                # Write plain text without timestamps
                f.write(result.text)
                f.write("\n")


class JSONFormatWriter(FormatWriter):
    """JSON format writer.

    Writes complete transcription data including metadata, segments,
    and speaker information (if available).
    """

    @property
    def extension(self) -> str:
        return "json"

    def write(self, result: TranscriptionResult, output_path: Path) -> None:
        """Write transcription as JSON."""
        data = {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "word_count": result.word_count(),
            "segment_count": result.segment_count(),
            "has_speakers": result.has_speakers(),
            "speakers": list(result.get_speakers()) if result.has_speakers() else [],
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "speaker": seg.speaker,
                }
                for seg in result.segments
            ],
            "metadata": result.metadata,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class SRTFormatWriter(FormatWriter):
    """SubRip (SRT) subtitle format writer.

    Standard subtitle format supported by most video players.
    Format:
        1
        00:00:00,000 --> 00:00:05,000
        First subtitle text

        2
        00:00:05,000 --> 00:00:10,000
        Second subtitle text
    """

    @property
    def extension(self) -> str:
        return "srt"

    def write(self, result: TranscriptionResult, output_path: Path) -> None:
        """Write transcription as SRT subtitles."""
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result.segments, start=1):
                # SRT uses commas for milliseconds, not periods
                start_time = self._format_srt_timestamp(segment.start)
                end_time = self._format_srt_timestamp(segment.end)

                # Add speaker prefix if available
                text = segment.text
                if segment.speaker:
                    text = f"[{segment.speaker}] {text}"

                # Write subtitle entry
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

    def _format_srt_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class VTTFormatWriter(FormatWriter):
    """WebVTT (VTT) subtitle format writer.

    Web Video Text Tracks format, used for HTML5 video subtitles.
    Format:
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        First subtitle text

        00:00:05.000 --> 00:00:10.000
        Second subtitle text
    """

    @property
    def extension(self) -> str:
        return "vtt"

    def write(self, result: TranscriptionResult, output_path: Path) -> None:
        """Write transcription as VTT subtitles."""
        with open(output_path, "w", encoding="utf-8") as f:
            # VTT files must start with "WEBVTT"
            f.write("WEBVTT\n\n")

            for segment in result.segments:
                # VTT uses periods for milliseconds
                start_time = self._format_vtt_timestamp(segment.start)
                end_time = self._format_vtt_timestamp(segment.end)

                # Add speaker prefix if available
                text = segment.text
                if segment.speaker:
                    text = f"<v {segment.speaker}>{text}"

                # Write subtitle entry
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

    def _format_vtt_timestamp(self, seconds: float) -> str:
        """Format timestamp for VTT format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# Format writer registry
_FORMAT_WRITERS: dict[str, Type[FormatWriter]] = {
    "txt": TXTFormatWriter,
    "json": JSONFormatWriter,
    "srt": SRTFormatWriter,
    "vtt": VTTFormatWriter,
}


def get_format_writer(format_name: str, **kwargs) -> FormatWriter:
    """Get format writer instance by name.

    Args:
        format_name: Format name (txt, json, srt, vtt)
        **kwargs: Additional arguments passed to writer constructor

    Returns:
        FormatWriter instance

    Raises:
        ValueError: If format is not supported
    """
    format_name = format_name.lower()
    if format_name not in _FORMAT_WRITERS:
        supported = ", ".join(_FORMAT_WRITERS.keys())
        raise ValueError(f"Unsupported format: {format_name}. Supported formats: {supported}")

    writer_class = _FORMAT_WRITERS[format_name]
    return writer_class(**kwargs)


def get_supported_formats() -> list[str]:
    """Get list of supported output formats.

    Returns:
        List of format names
    """
    return list(_FORMAT_WRITERS.keys())
