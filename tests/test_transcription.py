"""Tests for transcription module."""

import json
import tempfile
from pathlib import Path

import pytest

from retrocast.transcription.base import (
    TranscriptionBackend,
    TranscriptionResult,
    TranscriptionSegment,
)
from retrocast.transcription.output_formats import (
    JSONFormatWriter,
    SRTFormatWriter,
    TXTFormatWriter,
    VTTFormatWriter,
    get_format_writer,
    get_supported_formats,
)
from retrocast.transcription.utils import (
    compute_audio_hash,
    format_duration,
    format_timestamp,
    sanitize_for_path,
)


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment dataclass."""

    def test_segment_creation(self):
        """Test creating a transcription segment."""
        segment = TranscriptionSegment(
            start=0.0, end=5.0, text="Hello world", speaker=None
        )
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.text == "Hello world"
        assert segment.speaker is None

    def test_segment_duration(self):
        """Test segment duration calculation."""
        segment = TranscriptionSegment(start=10.5, end=15.7, text="Test")
        assert segment.duration() == pytest.approx(5.2)

    def test_segment_with_speaker(self):
        """Test segment with speaker diarization."""
        segment = TranscriptionSegment(
            start=0.0, end=5.0, text="Hello", speaker="SPEAKER_1"
        )
        assert segment.speaker == "SPEAKER_1"
        assert "[SPEAKER_1]" in str(segment)


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_result_creation(self):
        """Test creating a transcription result."""
        segments = [
            TranscriptionSegment(0.0, 5.0, "Hello world"),
            TranscriptionSegment(5.0, 10.0, "This is a test"),
        ]
        result = TranscriptionResult(
            segments=segments,
            text="Hello world This is a test",
            language="en",
            duration=10.0,
        )
        assert len(result.segments) == 2
        assert result.language == "en"
        assert result.duration == 10.0

    def test_word_count(self):
        """Test word count calculation."""
        result = TranscriptionResult(
            segments=[],
            text="Hello world this is a test",
            language="en",
            duration=10.0,
        )
        assert result.word_count() == 6

    def test_segment_count(self):
        """Test segment count."""
        segments = [
            TranscriptionSegment(0.0, 5.0, "One"),
            TranscriptionSegment(5.0, 10.0, "Two"),
            TranscriptionSegment(10.0, 15.0, "Three"),
        ]
        result = TranscriptionResult(
            segments=segments, text="One Two Three", language="en", duration=15.0
        )
        assert result.segment_count() == 3

    def test_has_speakers(self):
        """Test speaker detection."""
        segments_without_speakers = [
            TranscriptionSegment(0.0, 5.0, "Hello"),
        ]
        result_no_speakers = TranscriptionResult(
            segments=segments_without_speakers,
            text="Hello",
            language="en",
            duration=5.0,
        )
        assert not result_no_speakers.has_speakers()

        segments_with_speakers = [
            TranscriptionSegment(0.0, 5.0, "Hello", speaker="SPEAKER_1"),
        ]
        result_with_speakers = TranscriptionResult(
            segments=segments_with_speakers,
            text="Hello",
            language="en",
            duration=5.0,
        )
        assert result_with_speakers.has_speakers()

    def test_get_speakers(self):
        """Test getting unique speakers."""
        segments = [
            TranscriptionSegment(0.0, 5.0, "Hello", speaker="SPEAKER_1"),
            TranscriptionSegment(5.0, 10.0, "Hi", speaker="SPEAKER_2"),
            TranscriptionSegment(10.0, 15.0, "Hey", speaker="SPEAKER_1"),
        ]
        result = TranscriptionResult(
            segments=segments, text="Hello Hi Hey", language="en", duration=15.0
        )
        speakers = result.get_speakers()
        assert len(speakers) == 2
        assert "SPEAKER_1" in speakers
        assert "SPEAKER_2" in speakers


class TestUtils:
    """Tests for utility functions."""

    def test_sanitize_for_path(self):
        """Test path sanitization."""
        assert sanitize_for_path("Hello World") == "Hello World"
        assert sanitize_for_path("Hello/World") == "Hello-World"
        assert sanitize_for_path("Hello\\World") == "Hello-World"
        assert sanitize_for_path("Hello:World") == "HelloWorld"
        assert sanitize_for_path("Hello|World") == "HelloWorld"
        assert sanitize_for_path("Hello?World") == "HelloWorld"
        assert sanitize_for_path("Hello*World") == "HelloWorld"

    def test_sanitize_multiple_spaces(self):
        """Test sanitization of multiple spaces."""
        assert sanitize_for_path("Hello   World") == "Hello World"

    def test_sanitize_max_length(self):
        """Test max length truncation."""
        long_text = "A" * 250
        result = sanitize_for_path(long_text, max_length=100)
        assert len(result) == 100

    def test_sanitize_empty(self):
        """Test sanitization of empty/invalid strings."""
        assert sanitize_for_path("") == "untitled"
        assert sanitize_for_path("...") == "untitled"

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(65) == "01:05"
        assert format_duration(3665) == "01:01:05"
        assert format_duration(0) == "00:00"

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        assert format_timestamp(65.5) == "00:01:05.500"
        assert format_timestamp(3665.123) == "01:01:05.123"

    def test_compute_audio_hash(self):
        """Test audio hash computation."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)
            f.write(b"test audio content")

        try:
            # Compute hash
            hash1 = compute_audio_hash(test_path)
            assert len(hash1) == 64  # SHA256 produces 64 hex characters
            assert isinstance(hash1, str)

            # Verify hash is consistent
            hash2 = compute_audio_hash(test_path)
            assert hash1 == hash2
        finally:
            test_path.unlink()

    def test_compute_audio_hash_missing_file(self):
        """Test hash computation with missing file."""
        with pytest.raises(FileNotFoundError):
            compute_audio_hash(Path("/nonexistent/file.mp3"))


class TestFormatWriters:
    """Tests for output format writers."""

    @pytest.fixture
    def sample_result(self):
        """Create a sample transcription result for testing."""
        segments = [
            TranscriptionSegment(0.0, 5.0, "Hello world"),
            TranscriptionSegment(5.0, 10.0, "This is a test", speaker="SPEAKER_1"),
        ]
        return TranscriptionResult(
            segments=segments,
            text="Hello world This is a test",
            language="en",
            duration=10.0,
            metadata={"backend": "test", "model": "base"},
        )

    def test_get_supported_formats(self):
        """Test getting supported formats."""
        formats = get_supported_formats()
        assert "txt" in formats
        assert "json" in formats
        assert "srt" in formats
        assert "vtt" in formats

    def test_get_format_writer(self):
        """Test getting format writers."""
        txt_writer = get_format_writer("txt")
        assert isinstance(txt_writer, TXTFormatWriter)

        json_writer = get_format_writer("json")
        assert isinstance(json_writer, JSONFormatWriter)

        srt_writer = get_format_writer("srt")
        assert isinstance(srt_writer, SRTFormatWriter)

        vtt_writer = get_format_writer("vtt")
        assert isinstance(vtt_writer, VTTFormatWriter)

    def test_get_format_writer_invalid(self):
        """Test getting invalid format writer."""
        with pytest.raises(ValueError):
            get_format_writer("invalid")

    def test_txt_format_writer(self, sample_result):
        """Test TXT format writer."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            writer = TXTFormatWriter(include_timestamps=True)
            writer.write(sample_result, output_path)

            content = output_path.read_text(encoding="utf-8")
            assert "Hello world" in content
            assert "This is a test" in content
            assert "[00:00:00.000]" in content
            assert "[SPEAKER_1]" in content
        finally:
            output_path.unlink()

    def test_txt_format_writer_no_timestamps(self, sample_result):
        """Test TXT format writer without timestamps."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            writer = TXTFormatWriter(include_timestamps=False)
            writer.write(sample_result, output_path)

            content = output_path.read_text(encoding="utf-8")
            assert "Hello world This is a test" in content
            assert "[00:00:00" not in content
        finally:
            output_path.unlink()

    def test_json_format_writer(self, sample_result):
        """Test JSON format writer."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            writer = JSONFormatWriter()
            writer.write(sample_result, output_path)

            content = output_path.read_text(encoding="utf-8")
            data = json.loads(content)

            assert data["text"] == "Hello world This is a test"
            assert data["language"] == "en"
            assert data["duration"] == 10.0
            assert len(data["segments"]) == 2
            assert data["segments"][0]["text"] == "Hello world"
            assert data["segments"][1]["speaker"] == "SPEAKER_1"
        finally:
            output_path.unlink()

    def test_srt_format_writer(self, sample_result):
        """Test SRT format writer."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            writer = SRTFormatWriter()
            writer.write(sample_result, output_path)

            content = output_path.read_text(encoding="utf-8")
            assert "1\n" in content
            assert "2\n" in content
            assert "00:00:00,000 --> 00:00:05,000" in content
            assert "Hello world" in content
            assert "[SPEAKER_1]" in content
        finally:
            output_path.unlink()

    def test_vtt_format_writer(self, sample_result):
        """Test VTT format writer."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".vtt", delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            writer = VTTFormatWriter()
            writer.write(sample_result, output_path)

            content = output_path.read_text(encoding="utf-8")
            assert "WEBVTT\n" in content
            assert "00:00:00.000 --> 00:00:05.000" in content
            assert "Hello world" in content
            assert "<v SPEAKER_1>" in content
        finally:
            output_path.unlink()


class TestTranscriptionBackend:
    """Tests for TranscriptionBackend abstract class."""

    def test_backend_is_abstract(self):
        """Test that TranscriptionBackend cannot be instantiated."""
        with pytest.raises(TypeError):
            TranscriptionBackend()


class TestMLXWhisperBackend:
    """Tests for MLX Whisper backend."""

    def test_backend_name(self):
        """Test backend name property."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        backend = MLXWhisperBackend()
        assert backend.name == "mlx-whisper"

    def test_platform_info(self):
        """Test platform info."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        backend = MLXWhisperBackend()
        assert "Apple Silicon" in backend.platform_info()

    def test_description(self):
        """Test backend description."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        backend = MLXWhisperBackend()
        description = backend.description()
        assert "MLX" in description
        assert "Apple Silicon" in description

    def test_is_available_no_import(self, monkeypatch):
        """Test is_available when mlx_whisper not installed."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        # Mock the import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "mlx_whisper":
                raise ImportError("mlx_whisper not found")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        backend = MLXWhisperBackend()
        assert not backend.is_available()

    def test_is_available_wrong_platform(self, monkeypatch):
        """Test is_available on non-Darwin platform."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        # Mock platform.system to return Linux
        monkeypatch.setattr("platform.system", lambda: "Linux")

        backend = MLXWhisperBackend()
        # Should return False because platform is not Darwin
        assert not backend.is_available()

    def test_invalid_model_size(self):
        """Test transcribe with invalid model size."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        backend = MLXWhisperBackend()

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            test_path = Path(f.name)
            f.write(b"fake audio data")

        try:
            # This should fail even before trying to import mlx_whisper
            with pytest.raises((ValueError, ImportError)):
                backend.transcribe(test_path, model_size="invalid")
        finally:
            test_path.unlink()

    def test_transcribe_missing_file(self):
        """Test transcribe with missing audio file."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        backend = MLXWhisperBackend()

        # mlx_whisper not installed, so this should raise ImportError
        # (not FileNotFoundError which comes after the import check)
        with pytest.raises(ImportError, match="mlx_whisper is not installed"):
            backend.transcribe(Path("/nonexistent/file.mp3"))

    def test_convert_result(self):
        """Test conversion of mlx_whisper result to TranscriptionResult."""
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        backend = MLXWhisperBackend()
        backend._current_model_size = "base"

        # Mock mlx_whisper result
        mlx_result = {
            "text": "Hello world. This is a test.",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": " Hello world."},
                {"start": 2.5, "end": 5.0, "text": " This is a test."},
            ],
            "language": "en",
        }

        result = backend._convert_result(mlx_result, Path("test.mp3"))

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world. This is a test."
        assert result.language == "en"
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello world."
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 2.5
        assert result.duration == 5.0


class TestBackendRegistry:
    """Tests for backend registry."""

    def test_get_all_backends_includes_mlx(self):
        """Test that MLX backend is registered."""
        from retrocast.transcription.backends import get_all_backends

        backends = get_all_backends()
        backend_names = [b().name for b in backends]

        # MLX backend should be registered (even if not available)
        assert "mlx-whisper" in backend_names

    def test_backend_registration(self):
        """Test backend registration mechanism."""
        from retrocast.transcription.backends import (
            get_all_backends,
            register_backend,
        )
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        # Get initial count
        initial_backends = get_all_backends()

        # Register a backend (should be idempotent)
        register_backend(MLXWhisperBackend)

        # Should not duplicate
        after_backends = get_all_backends()
        assert len(after_backends) == len(initial_backends)
