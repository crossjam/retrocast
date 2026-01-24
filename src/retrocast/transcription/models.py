"""Pydantic models for transcription JSON output schema."""

from typing import Optional

from pydantic import BaseModel, Field


class TranscriptionSegmentModel(BaseModel):
    """Pydantic model for a transcription segment.

    This model validates the JSON structure of a single transcription segment
    with timing information and optional speaker attribution.

    Attributes:
        start: Start time in seconds
        end: End time in seconds
        text: Transcribed text for this segment
        speaker: Optional speaker identifier (used with diarization)
    """

    start: float = Field(..., description="Start time in seconds", ge=0.0)
    end: float = Field(..., description="End time in seconds", ge=0.0)
    text: str = Field(..., description="Transcribed text for this segment")
    speaker: Optional[str] = Field(None, description="Optional speaker identifier")

    model_config = {"extra": "forbid"}


class TranscriptionJSONModel(BaseModel):
    """Pydantic model for complete transcription JSON output.

    This model validates the complete JSON structure output by the
    JSONFormatWriter, including metadata, segments, and speaker information.

    Attributes:
        text: Full transcription text (concatenated from segments)
        language: Detected or specified language code (e.g., "en", "es")
        duration: Total audio duration in seconds
        word_count: Total number of words in transcription
        segment_count: Number of segments
        has_speakers: Whether transcription includes speaker diarization
        speakers: List of unique speaker identifiers
        segments: List of transcription segments with timing
        metadata: Additional metadata (model info, processing time, etc.)
    """

    text: str = Field(..., description="Full transcription text")
    language: str = Field(..., description="Language code (e.g., 'en', 'es')")
    duration: float = Field(..., description="Total audio duration in seconds", ge=0.0)
    word_count: int = Field(..., description="Total number of words", ge=0)
    segment_count: int = Field(..., description="Number of segments", ge=0)
    has_speakers: bool = Field(..., description="Whether speaker diarization is present")
    speakers: list[str] = Field(
        default_factory=list, description="List of unique speaker identifiers"
    )
    segments: list[TranscriptionSegmentModel] = Field(
        ..., description="List of transcription segments"
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    model_config = {"extra": "forbid"}
