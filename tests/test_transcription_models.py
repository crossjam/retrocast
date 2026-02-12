"""Tests for pydantic transcription models."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from retrocast.transcription.models import (
    TranscriptionJSONModel,
    TranscriptionSegmentModel,
)


class TestTranscriptionSegmentModel:
    """Tests for TranscriptionSegmentModel."""

    def test_valid_segment(self):
        """Test creating a valid segment model."""
        segment = TranscriptionSegmentModel(start=0.0, end=5.0, text="Hello world", speaker=None)
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.text == "Hello world"
        assert segment.speaker is None

    def test_segment_with_speaker(self):
        """Test segment with speaker diarization."""
        segment = TranscriptionSegmentModel(start=0.0, end=5.0, text="Hello", speaker="SPEAKER_1")
        assert segment.speaker == "SPEAKER_1"

    def test_negative_start_time(self):
        """Test that negative start time is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionSegmentModel(start=-1.0, end=5.0, text="Test")
        assert "start" in str(exc_info.value)

    def test_negative_end_time(self):
        """Test that negative end time is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionSegmentModel(start=0.0, end=-5.0, text="Test")
        assert "end" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            TranscriptionSegmentModel(start=0.0, end=5.0)  # missing text

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionSegmentModel(start=0.0, end=5.0, text="Test", extra_field="not allowed")
        assert "extra_field" in str(exc_info.value)

    def test_json_serialization(self):
        """Test JSON serialization of segment model."""
        segment = TranscriptionSegmentModel(
            start=0.0, end=5.0, text="Hello world", speaker="SPEAKER_1"
        )
        json_str = segment.model_dump_json()
        data = json.loads(json_str)
        assert data["start"] == 0.0
        assert data["end"] == 5.0
        assert data["text"] == "Hello world"
        assert data["speaker"] == "SPEAKER_1"

    def test_json_deserialization(self):
        """Test JSON deserialization to segment model."""
        json_data = {"start": 1.5, "end": 3.5, "text": "Test text", "speaker": None}
        segment = TranscriptionSegmentModel(**json_data)
        assert segment.start == 1.5
        assert segment.end == 3.5
        assert segment.text == "Test text"
        assert segment.speaker is None


class TestTranscriptionJSONModel:
    """Tests for TranscriptionJSONModel."""

    @pytest.fixture
    def valid_transcription_data(self) -> dict[str, Any]:
        """Fixture providing valid transcription data."""
        return {
            "text": "Hello world. This is a test.",
            "language": "en",
            "duration": 10.5,
            "word_count": 6,
            "segment_count": 2,
            "has_speakers": False,
            "speakers": [],
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hello world.", "speaker": None},
                {"start": 5.0, "end": 10.5, "text": "This is a test.", "speaker": None},
            ],
            "metadata": {"model": "base", "processing_time": 2.5},
        }

    def test_valid_transcription(self, valid_transcription_data):
        """Test creating a valid transcription model."""
        model = TranscriptionJSONModel(**valid_transcription_data)
        assert model.text == "Hello world. This is a test."
        assert model.language == "en"
        assert model.duration == 10.5
        assert model.word_count == 6
        assert model.segment_count == 2
        assert model.has_speakers is False
        assert model.speakers == []
        assert len(model.segments) == 2
        assert model.metadata == {"model": "base", "processing_time": 2.5}

    def test_transcription_with_speakers(self):
        """Test transcription with speaker diarization."""
        data = {
            "text": "Hello. Hi there.",
            "language": "en",
            "duration": 5.0,
            "word_count": 4,
            "segment_count": 2,
            "has_speakers": True,
            "speakers": ["SPEAKER_0", "SPEAKER_1"],
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Hello.", "speaker": "SPEAKER_0"},
                {"start": 2.0, "end": 5.0, "text": "Hi there.", "speaker": "SPEAKER_1"},
            ],
            "metadata": {},
        }
        model = TranscriptionJSONModel(**data)
        assert model.has_speakers is True
        assert set(model.speakers) == {"SPEAKER_0", "SPEAKER_1"}
        assert model.segments[0].speaker == "SPEAKER_0"
        assert model.segments[1].speaker == "SPEAKER_1"

    def test_negative_duration(self):
        """Test that negative duration is rejected."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": -1.0,  # Invalid
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionJSONModel(**data)
        assert "duration" in str(exc_info.value)

    def test_negative_word_count(self):
        """Test that negative word count is rejected."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "word_count": -1,  # Invalid
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionJSONModel(**data)
        assert "word_count" in str(exc_info.value)

    def test_negative_segment_count(self):
        """Test that negative segment count is rejected."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "word_count": 1,
            "segment_count": -1,  # Invalid
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionJSONModel(**data)
        assert "segment_count" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            TranscriptionJSONModel(
                text="Test",
                language="en",
                # Missing other required fields
            )

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {},
            "extra_field": "not allowed",  # Invalid
        }
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionJSONModel(**data)
        assert "extra_field" in str(exc_info.value)

    def test_json_serialization(self, valid_transcription_data):
        """Test JSON serialization of transcription model."""
        model = TranscriptionJSONModel(**valid_transcription_data)
        json_str = model.model_dump_json()
        data = json.loads(json_str)
        assert data["text"] == "Hello world. This is a test."
        assert data["language"] == "en"
        assert data["duration"] == 10.5
        assert len(data["segments"]) == 2

    def test_json_deserialization(self, valid_transcription_data):
        """Test JSON deserialization to transcription model."""
        # First serialize
        model = TranscriptionJSONModel(**valid_transcription_data)
        json_str = model.model_dump_json()

        # Then deserialize
        data = json.loads(json_str)
        model2 = TranscriptionJSONModel(**data)
        assert model2.text == model.text
        assert model2.language == model.language
        assert model2.duration == model.duration
        assert len(model2.segments) == len(model.segments)

    def test_empty_segments_list(self):
        """Test transcription with empty segments list."""
        data = {
            "text": "",
            "language": "en",
            "duration": 0.0,
            "word_count": 0,
            "segment_count": 0,
            "has_speakers": False,
            "speakers": [],
            "segments": [],  # Empty list
            "metadata": {},
        }
        model = TranscriptionJSONModel(**data)
        assert model.segments == []
        assert model.segment_count == 0

    def test_invalid_segment_in_list(self):
        """Test that invalid segment in list raises validation error."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [
                {"start": -1.0, "end": 1.0, "text": "Test", "speaker": None}  # Invalid start
            ],
            "metadata": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionJSONModel(**data)
        assert "segments" in str(exc_info.value)

    def test_empty_metadata(self):
        """Test transcription with empty metadata dict."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {},
        }
        model = TranscriptionJSONModel(**data)
        assert model.metadata == {}

    def test_complex_metadata(self):
        """Test transcription with complex metadata."""
        data = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {
                "model": "large-v3",
                "processing_time": 45.2,
                "device": "cuda",
                "nested": {"key": "value"},
            },
        }
        model = TranscriptionJSONModel(**data)
        assert model.metadata["model"] == "large-v3"
        assert model.metadata["nested"]["key"] == "value"
