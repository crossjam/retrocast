"""Integration test showing pydantic model validation of JSONFormatWriter output."""

import json
import tempfile
from pathlib import Path

from retrocast.transcription.base import TranscriptionResult, TranscriptionSegment
from retrocast.transcription.models import TranscriptionJSONModel
from retrocast.transcription.output_formats import JSONFormatWriter


def test_json_writer_output_validates_with_pydantic():
    """Test that JSONFormatWriter output can be validated by TranscriptionJSONModel."""
    # Create a sample transcription result
    segments = [
        TranscriptionSegment(start=0.0, end=5.0, text="Hello world.", speaker=None),
        TranscriptionSegment(start=5.0, end=10.5, text="This is a test.", speaker=None),
    ]
    result = TranscriptionResult(
        segments=segments,
        text="Hello world. This is a test.",
        language="en",
        duration=10.5,
        metadata={"model": "base", "processing_time": 2.5},
    )

    # Write to JSON file using JSONFormatWriter
    writer = JSONFormatWriter()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test.json"
        writer.write(result, output_path)

        # Read the JSON file and validate with pydantic
        with open(output_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # This should not raise a validation error
        validated_model = TranscriptionJSONModel(**json_data)

        # Verify the data matches
        assert validated_model.text == result.text
        assert validated_model.language == result.language
        assert validated_model.duration == result.duration
        assert validated_model.word_count == result.word_count()
        assert validated_model.segment_count == result.segment_count()
        assert validated_model.has_speakers == result.has_speakers()
        assert len(validated_model.segments) == len(result.segments)


def test_json_writer_with_speakers_validates():
    """Test that JSONFormatWriter output with speakers validates correctly."""
    # Create a transcription result with speakers
    segments = [
        TranscriptionSegment(start=0.0, end=2.0, text="Hello.", speaker="SPEAKER_0"),
        TranscriptionSegment(start=2.0, end=5.0, text="Hi there.", speaker="SPEAKER_1"),
    ]
    result = TranscriptionResult(
        segments=segments,
        text="Hello. Hi there.",
        language="en",
        duration=5.0,
        metadata={"diarization": True},
    )

    # Write to JSON file using JSONFormatWriter
    writer = JSONFormatWriter()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test.json"
        writer.write(result, output_path)

        # Read the JSON file and validate with pydantic
        with open(output_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # This should not raise a validation error
        validated_model = TranscriptionJSONModel(**json_data)

        # Verify speaker information
        assert validated_model.has_speakers is True
        assert set(validated_model.speakers) == {"SPEAKER_0", "SPEAKER_1"}
        assert validated_model.segments[0].speaker == "SPEAKER_0"
        assert validated_model.segments[1].speaker == "SPEAKER_1"
