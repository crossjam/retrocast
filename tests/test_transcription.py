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
        segment = TranscriptionSegment(start=0.0, end=5.0, text="Hello world", speaker=None)
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
        segment = TranscriptionSegment(start=0.0, end=5.0, text="Hello", speaker="SPEAKER_1")
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".vtt", delete=False) as f:
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

        # If mlx_whisper is not installed, should raise ImportError
        # If mlx_whisper IS installed, should raise FileNotFoundError
        with pytest.raises((ImportError, FileNotFoundError)):
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


class TestFasterWhisperBackend:
    """Tests for Faster-Whisper backend."""

    def test_backend_name(self):
        """Test backend name property."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()
        assert backend.name == "faster-whisper"

    def test_platform_info_cpu(self):
        """Test platform info for CPU."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()
        backend._device = "cpu"
        platform_info = backend.platform_info()
        assert "CPU" in platform_info

    def test_platform_info_cuda(self):
        """Test platform info for CUDA."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()
        backend._device = "cuda"
        platform_info = backend.platform_info()
        assert "CUDA" in platform_info or "GPU" in platform_info

    def test_description(self):
        """Test backend description."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()
        description = backend.description()
        assert "Faster-Whisper" in description
        assert "CUDA" in description or "CPU" in description

    def test_is_available_no_import(self, monkeypatch):
        """Test is_available when faster_whisper not installed."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        # Mock the import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "faster_whisper":
                raise ImportError("faster_whisper not found")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        backend = FasterWhisperBackend()
        assert not backend.is_available()

    def test_detect_device_cpu(self, monkeypatch):
        """Test device detection defaults to CPU when CUDA not available."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()

        # Mock torch to not have CUDA
        class MockTorch:
            class cuda:
                @staticmethod
                def is_available():
                    return False

        monkeypatch.setattr(
            "retrocast.transcription.backends.faster_whisper.torch",
            MockTorch,
            raising=False,
        )

        device, compute_type = backend._detect_device()
        assert device == "cpu"
        assert compute_type == "int8"

    def test_invalid_model_size(self):
        """Test transcribe with invalid model size."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            test_path = Path(f.name)
            f.write(b"fake audio data")

        try:
            # This should fail with ValueError for invalid model size
            with pytest.raises((ValueError, ImportError)):
                backend.transcribe(test_path, model_size="invalid")
        finally:
            test_path.unlink()

    def test_transcribe_missing_file(self):
        """Test transcribe with missing audio file."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()

        # If faster_whisper is not installed, should raise ImportError
        # If faster_whisper IS installed, should raise FileNotFoundError
        with pytest.raises((ImportError, FileNotFoundError)):
            backend.transcribe(Path("/nonexistent/file.mp3"))

    def test_convert_result(self):
        """Test conversion of faster_whisper result to TranscriptionResult."""
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        backend = FasterWhisperBackend()
        backend._device = "cpu"
        backend._compute_type = "int8"

        # Mock faster_whisper segment objects
        class MockSegment:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text

        class MockInfo:
            def __init__(self):
                self.language = "en"
                self.duration = 5.0
                self.language_probability = 0.95

        faster_segments = [
            MockSegment(0.0, 2.5, " Hello world."),
            MockSegment(2.5, 5.0, " This is a test."),
        ]
        info = MockInfo()

        result = backend._convert_result(
            faster_segments, info, Path("test.mp3"), transcription_time=2.5, model_size="base"
        )

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world. This is a test."
        assert result.language == "en"
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello world."
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 2.5
        assert result.duration == 5.0
        assert result.metadata["backend"] == "faster-whisper"
        assert result.metadata["device"] == "cpu"
        assert result.metadata["transcription_time"] == 2.5


class TestBackendRegistry:
    """Tests for backend registry."""

    def test_get_all_backends_includes_mlx(self):
        """Test that MLX backend is registered."""
        from retrocast.transcription.backends import get_all_backends

        backends = get_all_backends()
        backend_names = [b().name for b in backends]

        # MLX backend should be registered (even if not available)
        assert "mlx-whisper" in backend_names

    def test_get_all_backends_includes_faster_whisper(self):
        """Test that Faster-Whisper backend is registered."""
        from retrocast.transcription.backends import get_all_backends

        backends = get_all_backends()
        backend_names = [b().name for b in backends]

        # Faster-Whisper backend should be registered (even if not available)
        assert "faster-whisper" in backend_names

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


class TestTranscriptionDatabase:
    """Tests for transcription database operations."""

    def test_upsert_transcription_success(self):
        """Test successful transcription insertion."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Create test segments
            segments = [
                {"start": 0.0, "end": 5.0, "text": "Hello world", "speaker": None},
                {"start": 5.0, "end": 10.0, "text": "Test segment", "speaker": None},
            ]

            # Insert transcription
            transcription_id = ds.upsert_transcription(
                audio_content_hash="abc123",
                media_path="/path/to/test.mp3",
                file_size=1024,
                transcription_path="/path/to/test.json",
                episode_url="http://example.com/episode",
                podcast_title="Test Podcast",
                episode_title="Test Episode",
                backend="mlx-whisper",
                model_size="base",
                language="en",
                duration=10.0,
                transcription_time=5.0,
                has_diarization=False,
                speaker_count=0,
                word_count=10,
                segments=segments,
            )

            assert isinstance(transcription_id, int)
            assert transcription_id > 0

            # Verify record exists
            record = ds.db["transcriptions"].get(transcription_id)
            assert record["audio_content_hash"] == "abc123"
            assert record["podcast_title"] == "Test Podcast"
            assert record["backend"] == "mlx-whisper"

            # Verify segments were saved
            segment_count = ds.db.execute(
                "SELECT COUNT(*) FROM transcription_segments WHERE transcription_id = ?",
                [transcription_id],
            ).fetchone()[0]
            assert segment_count == 2

    def test_upsert_transcription_update_existing(self):
        """Test updating an existing transcription."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            segments = [{"start": 0.0, "end": 5.0, "text": "First version", "speaker": None}]

            # Insert initial transcription
            transcription_id_1 = ds.upsert_transcription(
                audio_content_hash="same_hash",
                media_path="/path/to/test.mp3",
                file_size=1024,
                transcription_path="/path/to/test.json",
                episode_url="http://example.com/episode",
                podcast_title="Test Podcast",
                episode_title="Test Episode",
                backend="mlx-whisper",
                model_size="base",
                language="en",
                duration=5.0,
                transcription_time=2.0,
                has_diarization=False,
                speaker_count=0,
                word_count=5,
                segments=segments,
            )

            # Update with same hash but different model
            segments_v2 = [{"start": 0.0, "end": 5.0, "text": "Updated version", "speaker": None}]

            transcription_id_2 = ds.upsert_transcription(
                audio_content_hash="same_hash",  # Same hash
                media_path="/path/to/test.mp3",
                file_size=1024,
                transcription_path="/path/to/test.json",
                episode_url="http://example.com/episode",
                podcast_title="Test Podcast",
                episode_title="Test Episode",
                backend="mlx-whisper",
                model_size="large",  # Different model
                language="en",
                duration=5.0,
                transcription_time=10.0,  # Different time
                has_diarization=False,
                speaker_count=0,
                word_count=6,
                segments=segments_v2,
            )

            # Should return same ID (updated, not inserted)
            assert transcription_id_1 == transcription_id_2

            # Verify record was updated
            record = ds.db["transcriptions"].get(transcription_id_2)
            assert record["model_size"] == "large"
            assert record["transcription_time"] == 10.0

            # Verify only one record exists for this hash
            count = ds.db.execute(
                "SELECT COUNT(*) FROM transcriptions WHERE audio_content_hash = ?",
                ["same_hash"],
            ).fetchone()[0]
            assert count == 1

    def test_search_transcriptions(self):
        """Test full-text search of transcriptions."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert test transcription
            segments = [
                {"start": 0.0, "end": 5.0, "text": "Machine learning is amazing", "speaker": None},
                {"start": 5.0, "end": 10.0, "text": "Python programming tutorial", "speaker": None},
            ]

            ds.upsert_transcription(
                audio_content_hash="search_test",
                media_path="/path/to/test.mp3",
                file_size=1024,
                transcription_path="/path/to/test.json",
                episode_url="http://example.com/episode",
                podcast_title="Tech Podcast",
                episode_title="ML Episode",
                backend="mlx-whisper",
                model_size="base",
                language="en",
                duration=10.0,
                transcription_time=5.0,
                has_diarization=False,
                speaker_count=0,
                word_count=20,
                segments=segments,
            )

            # Search for "machine learning"
            results = ds.search_transcriptions("machine learning", limit=10)
            assert len(results) > 0

            # Verify result contains expected fields
            result = results[0]
            assert "text" in result
            assert "podcast_title" in result
            assert "episode_title" in result
            assert "machine learning" in result["text"].lower()

    def test_search_transcriptions_with_podcast_filter(self):
        """Test searching with podcast filter."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert transcriptions for different podcasts
            for i, podcast in enumerate(["Podcast A", "Podcast B"]):
                segments = [
                    {"start": 0.0, "end": 5.0, "text": f"Python tutorial {i}", "speaker": None}
                ]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=f"http://example.com/episode{i}",
                    podcast_title=podcast,
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=5.0,
                    transcription_time=2.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=10,
                    segments=segments,
                )

            # Search only in Podcast A
            results = ds.search_transcriptions("Python", podcast_title="Podcast A", limit=10)
            assert len(results) > 0

            # All results should be from Podcast A
            for result in results:
                assert result["podcast_title"] == "Podcast A"

    def test_search_transcriptions_with_backend_filter(self):
        """Test searching with backend filter."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert transcriptions with different backends
            for backend in ["mlx-whisper", "faster-whisper"]:
                segments = [{"start": 0.0, "end": 5.0, "text": "Test content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_{backend}",
                    media_path=f"/path/to/{backend}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/{backend}.json",
                    episode_url=None,
                    podcast_title="Test Podcast",
                    episode_title=f"Episode {backend}",
                    backend=backend,
                    model_size="base",
                    language="en",
                    duration=10.0,
                    transcription_time=5.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            # Search with backend filter
            results = ds.search_transcriptions("Test", backend="mlx-whisper")
            assert len(results) > 0
            for result in results:
                assert result["backend"] == "mlx-whisper"

    def test_search_transcriptions_with_model_filter(self):
        """Test searching with model size filter."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert transcriptions with different models
            for model in ["base", "medium"]:
                segments = [{"start": 0.0, "end": 5.0, "text": "AI content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_{model}",
                    media_path=f"/path/to/{model}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/{model}.json",
                    episode_url=None,
                    podcast_title="AI Podcast",
                    episode_title=f"Episode {model}",
                    backend="mlx-whisper",
                    model_size=model,
                    language="en",
                    duration=10.0,
                    transcription_time=5.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            # Search with model filter
            results = ds.search_transcriptions("AI", model_size="medium")
            assert len(results) > 0
            for result in results:
                assert result["model_size"] == "medium"

    def test_search_transcriptions_with_date_range(self):
        """Test searching with date range filter."""
        from datetime import datetime, timedelta

        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert a transcription
            segments = [{"start": 0.0, "end": 5.0, "text": "Date test content", "speaker": None}]
            ds.upsert_transcription(
                audio_content_hash="hash_date",
                media_path="/path/to/test.mp3",
                file_size=1024,
                transcription_path="/path/to/test.json",
                episode_url=None,
                podcast_title="Date Podcast",
                episode_title="Date Episode",
                backend="mlx-whisper",
                model_size="base",
                language="en",
                duration=10.0,
                transcription_time=5.0,
                has_diarization=False,
                speaker_count=0,
                word_count=100,
                segments=segments,
            )

            # Search with date range (should find it)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
            results = ds.search_transcriptions("Date", date_from=yesterday, date_to=tomorrow)
            assert len(results) > 0

            # Search with date range that excludes it (future dates)
            future_start = (datetime.now() + timedelta(days=2)).isoformat()
            future_end = (datetime.now() + timedelta(days=3)).isoformat()
            results = ds.search_transcriptions("Date", date_from=future_start, date_to=future_end)
            assert len(results) == 0

    def test_search_transcriptions_with_context(self):
        """Test searching with context segments."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert transcription with multiple segments
            segments = [
                {"start": 0.0, "end": 5.0, "text": "First segment", "speaker": None},
                {"start": 5.0, "end": 10.0, "text": "Machine learning content", "speaker": None},
                {"start": 10.0, "end": 15.0, "text": "Last segment", "speaker": None},
            ]
            ds.upsert_transcription(
                audio_content_hash="hash_context",
                media_path="/path/to/test.mp3",
                file_size=1024,
                transcription_path="/path/to/test.json",
                episode_url=None,
                podcast_title="Context Podcast",
                episode_title="Context Episode",
                backend="mlx-whisper",
                model_size="base",
                language="en",
                duration=15.0,
                transcription_time=7.5,
                has_diarization=False,
                speaker_count=0,
                word_count=150,
                segments=segments,
            )

            # Search with context
            results = ds.search_transcriptions("machine learning", context_segments=1)
            assert len(results) > 0

            # Verify context segments are present
            result = results[0]
            assert "context_before" in result
            assert "context_after" in result
            assert len(result["context_before"]) == 1
            assert len(result["context_after"]) == 1
            assert "First segment" in result["context_before"][0]["text"]
            assert "Last segment" in result["context_after"][0]["text"]

    def test_search_transcriptions_with_pagination(self):
        """Test searching with pagination (limit and offset)."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert multiple transcriptions
            for i in range(5):
                segments = [
                    {"start": 0.0, "end": 5.0, "text": f"Python tutorial part {i}", "speaker": None}
                ]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_page_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title="Tutorial Podcast",
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=10.0,
                    transcription_time=5.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            # First page
            results_page1 = ds.search_transcriptions("Python", limit=2, offset=0)
            assert len(results_page1) == 2

            # Second page
            results_page2 = ds.search_transcriptions("Python", limit=2, offset=2)
            assert len(results_page2) == 2

            # Results should be different
            assert results_page1[0]["media_path"] != results_page2[0]["media_path"]


class TestTranscriptionSummaryMethods:
    """Tests for transcription summary and statistics methods."""

    def test_get_transcription_summary_empty(self):
        """Test summary with no transcriptions."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            summary = ds.get_transcription_summary()

            assert summary["total_transcriptions"] == 0
            assert summary["total_podcasts"] == 0
            assert summary["total_segments"] == 0
            assert summary["total_words"] == 0
            assert summary["total_duration"] == 0.0
            assert summary["date_range"] == (None, None)
            assert summary["backends_used"] == {}
            assert summary["models_used"] == {}
            assert summary["languages"] == {}

    def test_get_transcription_summary_with_data(self):
        """Test summary with transcription data."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert test transcriptions
            for i, (podcast, backend, model, lang) in enumerate([
                ("Podcast A", "mlx-whisper", "base", "en"),
                ("Podcast A", "mlx-whisper", "medium", "en"),
                ("Podcast B", "faster-whisper", "base", "es"),
            ]):
                segments = [
                    {"start": 0.0, "end": 5.0, "text": f"Segment {i}", "speaker": None}
                ]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_summary_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title=podcast,
                    episode_title=f"Episode {i}",
                    backend=backend,
                    model_size=model,
                    language=lang,
                    duration=3600.0,  # 1 hour
                    transcription_time=300.0,  # 5 minutes
                    has_diarization=False,
                    speaker_count=0,
                    word_count=1000,
                    segments=segments,
                )

            summary = ds.get_transcription_summary()

            assert summary["total_transcriptions"] == 3
            assert summary["total_podcasts"] == 2
            assert summary["total_segments"] == 3
            assert summary["total_words"] == 3000
            assert summary["total_duration"] == 3.0  # 3 hours
            assert summary["total_transcription_time"] == 0.25  # 15 minutes = 0.25 hours
            assert "mlx-whisper" in summary["backends_used"]
            assert "faster-whisper" in summary["backends_used"]
            assert "base" in summary["models_used"]
            assert "medium" in summary["models_used"]
            assert "en" in summary["languages"]
            assert "es" in summary["languages"]
            assert summary["date_range"][0] is not None
            assert summary["date_range"][1] is not None

    def test_get_podcast_transcription_stats(self):
        """Test podcast-level statistics."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert transcriptions for two podcasts
            for i, podcast in enumerate(["Tech Podcast", "Tech Podcast", "News Podcast"]):
                segments = [
                    {"start": 0.0, "end": 5.0, "text": f"Content {i}", "speaker": None}
                ]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_podcast_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title=podcast,
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=3600.0,
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=500,
                    segments=segments,
                )

            stats = ds.get_podcast_transcription_stats()

            assert len(stats) == 2

            # Tech Podcast should be first (more episodes)
            tech_stats = next(s for s in stats if s["podcast_title"] == "Tech Podcast")
            assert tech_stats["episode_count"] == 2
            assert tech_stats["total_words"] == 1000
            assert tech_stats["total_segments"] == 2

            news_stats = next(s for s in stats if s["podcast_title"] == "News Podcast")
            assert news_stats["episode_count"] == 1
            assert news_stats["total_words"] == 500

    def test_get_podcast_transcription_stats_with_limit(self):
        """Test podcast stats with limit."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert transcriptions for 3 podcasts
            for i in range(3):
                segments = [{"start": 0.0, "end": 5.0, "text": "Content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_limit_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title=f"Podcast {i}",
                    episode_title="Episode",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=3600.0,
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            # Get only top 2
            stats = ds.get_podcast_transcription_stats(limit=2)
            assert len(stats) == 2

    def test_get_episode_transcription_list(self):
        """Test listing transcribed episodes."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert test transcriptions
            for i in range(3):
                segments = [{"start": 0.0, "end": 5.0, "text": f"Episode {i}", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_list_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title="Test Podcast",
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=float(i * 1000),
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=(i + 1) * 100,
                    segments=segments,
                )

            # Get all episodes
            episodes = ds.get_episode_transcription_list()
            assert len(episodes) == 3

            # Verify fields
            ep = episodes[0]
            assert "transcription_id" in ep
            assert "podcast_title" in ep
            assert "episode_title" in ep
            assert "duration" in ep
            assert "word_count" in ep

    def test_get_episode_transcription_list_with_filter(self):
        """Test listing episodes filtered by podcast."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert for different podcasts
            for i, podcast in enumerate(["Podcast A", "Podcast A", "Podcast B"]):
                segments = [{"start": 0.0, "end": 5.0, "text": "Content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_filter_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title=podcast,
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=3600.0,
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            # Filter by podcast
            episodes = ds.get_episode_transcription_list(podcast_title="Podcast A")
            assert len(episodes) == 2
            for ep in episodes:
                assert ep["podcast_title"] == "Podcast A"

    def test_get_episode_transcription_list_with_ordering(self):
        """Test listing episodes with different orderings."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Insert with different word counts
            for i, word_count in enumerate([100, 300, 200]):
                segments = [{"start": 0.0, "end": 5.0, "text": "Content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_order_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title="Test Podcast",
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=3600.0,
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=word_count,
                    segments=segments,
                )

            # Order by word_count descending
            episodes = ds.get_episode_transcription_list(order_by="word_count", order_desc=True)
            assert episodes[0]["word_count"] == 300
            assert episodes[1]["word_count"] == 200
            assert episodes[2]["word_count"] == 100

            # Order by word_count ascending
            episodes = ds.get_episode_transcription_list(order_by="word_count", order_desc=False)
            assert episodes[0]["word_count"] == 100
            assert episodes[2]["word_count"] == 300

    def test_count_transcriptions(self):
        """Test counting transcriptions."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Initially zero
            assert ds.count_transcriptions() == 0

            # Insert test transcriptions
            for i, podcast in enumerate(["Podcast A", "Podcast A", "Podcast B"]):
                segments = [{"start": 0.0, "end": 5.0, "text": "Content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_count_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title=podcast,
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=3600.0,
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            assert ds.count_transcriptions() == 3
            assert ds.count_transcriptions(podcast_title="Podcast A") == 2
            assert ds.count_transcriptions(podcast_title="Podcast B") == 1
            assert ds.count_transcriptions(podcast_title="Nonexistent") == 0

    def test_get_transcription_podcasts(self):
        """Test getting list of podcast titles with transcriptions."""
        from retrocast.datastore import Datastore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            ds = Datastore(db_path)

            # Initially empty
            assert ds.get_transcription_podcasts() == []

            # Insert for different podcasts
            for i, podcast in enumerate(["Zebra Podcast", "Alpha Podcast", "Alpha Podcast"]):
                segments = [{"start": 0.0, "end": 5.0, "text": "Content", "speaker": None}]
                ds.upsert_transcription(
                    audio_content_hash=f"hash_podcasts_{i}",
                    media_path=f"/path/to/test{i}.mp3",
                    file_size=1024,
                    transcription_path=f"/path/to/test{i}.json",
                    episode_url=None,
                    podcast_title=podcast,
                    episode_title=f"Episode {i}",
                    backend="mlx-whisper",
                    model_size="base",
                    language="en",
                    duration=3600.0,
                    transcription_time=300.0,
                    has_diarization=False,
                    speaker_count=0,
                    word_count=100,
                    segments=segments,
                )

            podcasts = ds.get_transcription_podcasts()
            assert len(podcasts) == 2
            # Should be sorted alphabetically
            assert podcasts[0] == "Alpha Podcast"
            assert podcasts[1] == "Zebra Podcast"
