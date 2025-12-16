"""Base classes and data models for transcription functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment with timing information.

    Attributes:
        start: Start time in seconds
        end: End time in seconds
        text: Transcribed text for this segment
        speaker: Optional speaker identifier (used with diarization)
    """

    start: float
    end: float
    text: str
    speaker: Optional[str] = None

    def duration(self) -> float:
        """Calculate segment duration in seconds."""
        return self.end - self.start

    def __str__(self) -> str:
        """Human-readable string representation."""
        speaker_prefix = f"[{self.speaker}] " if self.speaker else ""
        return f"[{self.start:.2f}s - {self.end:.2f}s] {speaker_prefix}{self.text}"


@dataclass
class TranscriptionResult:
    """Complete transcription result with all metadata.

    Attributes:
        segments: List of transcription segments with timing
        text: Full transcription text (concatenated from segments)
        language: Detected or specified language code (e.g., "en", "es")
        duration: Total audio duration in seconds
        metadata: Additional metadata (model info, processing time, etc.)
    """

    segments: list[TranscriptionSegment]
    text: str
    language: str
    duration: float
    metadata: dict = field(default_factory=dict)

    def word_count(self) -> int:
        """Count total words in transcription."""
        return len(self.text.split())

    def segment_count(self) -> int:
        """Get number of segments."""
        return len(self.segments)

    def has_speakers(self) -> bool:
        """Check if transcription includes speaker diarization."""
        return any(seg.speaker is not None for seg in self.segments)

    def get_speakers(self) -> set[str]:
        """Get set of unique speaker identifiers."""
        return {seg.speaker for seg in self.segments if seg.speaker is not None}


class TranscriptionBackend(ABC):
    """Abstract base class for transcription backends.

    All transcription backends (MLX Whisper, faster-whisper, etc.) must
    inherit from this class and implement the required methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend identifier (e.g., 'mlx-whisper', 'faster-whisper').

        Returns:
            Backend name string
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend dependencies are available.

        This method should attempt to import required libraries and verify
        that the backend can run on the current platform.

        Returns:
            True if backend is available, False otherwise
        """
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> TranscriptionResult:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., "en", "es"). If None, auto-detect.
            model_size: Model size to use (tiny, base, small, medium, large)

        Returns:
            TranscriptionResult with segments, text, and metadata

        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio format is unsupported
            RuntimeError: If transcription fails
        """
        pass

    def platform_info(self) -> str:
        """Return platform-specific information for this backend.

        Returns:
            Human-readable platform info (e.g., "macOS (Apple Silicon)", "Linux (CUDA)")
        """
        return "All platforms"

    def description(self) -> str:
        """Return a brief description of this backend.

        Returns:
            Human-readable description
        """
        return f"{self.name} transcription backend"
