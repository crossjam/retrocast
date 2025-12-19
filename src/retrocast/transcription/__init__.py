"""Transcription module for retrocast.

This module provides transcription functionality for podcast audio files
using various backends (MLX Whisper, faster-whisper, OpenAI Whisper).
"""

from retrocast.transcription.base import (
    TranscriptionBackend,
    TranscriptionResult,
    TranscriptionSegment,
)
from retrocast.transcription.output_formats import (
    FormatWriter,
    JSONFormatWriter,
    SRTFormatWriter,
    TXTFormatWriter,
    VTTFormatWriter,
    get_format_writer,
    get_supported_formats,
)
from retrocast.transcription.transcription_manager import TranscriptionManager

__all__ = [
    # Base classes and data models
    "TranscriptionBackend",
    "TranscriptionResult",
    "TranscriptionSegment",
    # Format writers
    "FormatWriter",
    "TXTFormatWriter",
    "JSONFormatWriter",
    "SRTFormatWriter",
    "VTTFormatWriter",
    "get_format_writer",
    "get_supported_formats",
    # Main manager
    "TranscriptionManager",
]
