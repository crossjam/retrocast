"""Tests for transcription validate command."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from retrocast.cli import cli


def test_validate_command_with_valid_files():
    """Test validate command with all valid JSON files."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "transcriptions" / "TestPodcast"
        output_dir.mkdir(parents=True)

        # Create valid JSON file
        valid_file = output_dir / "episode1.json"
        valid_data = {
            "text": "Hello world.",
            "language": "en",
            "duration": 5.0,
            "word_count": 2,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 5.0, "text": "Hello world.", "speaker": None}],
            "metadata": {},
        }
        with open(valid_file, "w") as f:
            json.dump(valid_data, f)

        # Run validate command
        result = runner.invoke(
            cli,
            ["transcribe", "validate", "--output-dir", str(Path(tmpdir) / "transcriptions")],
        )

        assert result.exit_code == 0
        assert "All transcription files are valid!" in result.output
        assert "1" in result.output  # File count


def test_validate_command_with_invalid_files():
    """Test validate command with invalid JSON files."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "transcriptions" / "TestPodcast"
        output_dir.mkdir(parents=True)

        # Create invalid JSON file (negative duration)
        invalid_file = output_dir / "invalid.json"
        invalid_data = {
            "text": "Test",
            "language": "en",
            "duration": -5.0,  # Invalid: negative
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test", "speaker": None}],
            "metadata": {},
        }
        with open(invalid_file, "w") as f:
            json.dump(invalid_data, f)

        # Run validate command
        result = runner.invoke(
            cli,
            ["transcribe", "validate", "--output-dir", str(Path(tmpdir) / "transcriptions")],
        )

        assert result.exit_code == 1
        assert "Invalid Schema" in result.output
        assert "invalid.json" in result.output


def test_validate_command_with_broken_json():
    """Test validate command with broken JSON files."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "transcriptions" / "TestPodcast"
        output_dir.mkdir(parents=True)

        # Create broken JSON file
        broken_file = output_dir / "broken.json"
        with open(broken_file, "w") as f:
            f.write("{ this is not valid JSON }")

        # Run validate command
        result = runner.invoke(
            cli,
            ["transcribe", "validate", "--output-dir", str(Path(tmpdir) / "transcriptions")],
        )

        assert result.exit_code == 1
        assert "Parse Errors" in result.output
        assert "broken.json" in result.output


def test_validate_command_verbose_mode():
    """Test validate command with verbose flag."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "transcriptions" / "TestPodcast"
        output_dir.mkdir(parents=True)

        # Create valid and invalid files
        valid_file = output_dir / "valid.json"
        valid_data = {
            "text": "Valid",
            "language": "en",
            "duration": 5.0,
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 5.0, "text": "Valid", "speaker": None}],
            "metadata": {},
        }
        with open(valid_file, "w") as f:
            json.dump(valid_data, f)

        invalid_file = output_dir / "invalid.json"
        invalid_data = {
            "text": "Invalid",
            "language": "en",
            "duration": -1.0,  # Invalid
            "word_count": 1,
            "segment_count": 1,
            "has_speakers": False,
            "speakers": [],
            "segments": [{"start": 0.0, "end": 1.0, "text": "Invalid", "speaker": None}],
            "metadata": {},
        }
        with open(invalid_file, "w") as f:
            json.dump(invalid_data, f)

        # Run validate command with verbose
        result = runner.invoke(
            cli,
            [
                "transcribe",
                "validate",
                "--output-dir",
                str(Path(tmpdir) / "transcriptions"),
                "--verbose",
            ],
        )

        assert result.exit_code == 1
        assert "✓" in result.output  # Valid marker
        assert "✗" in result.output  # Invalid marker
        assert "valid.json" in result.output
        assert "invalid.json" in result.output


def test_validate_command_no_files():
    """Test validate command when directory has no JSON files."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "transcriptions"
        output_dir.mkdir()

        # Run validate command
        result = runner.invoke(
            cli, ["transcribe", "validate", "--output-dir", str(output_dir)]
        )

        assert result.exit_code == 0
        assert "No JSON files found" in result.output


def test_validate_command_missing_directory():
    """Test validate command when directory doesn't exist."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent = Path(tmpdir) / "nonexistent"

        # Run validate command
        result = runner.invoke(
            cli, ["transcribe", "validate", "--output-dir", str(nonexistent)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output


def test_validate_command_with_speakers():
    """Test validate command with transcription containing speakers."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "transcriptions" / "TestPodcast"
        output_dir.mkdir(parents=True)

        # Create file with speakers
        speakers_file = output_dir / "with_speakers.json"
        speakers_data = {
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
        with open(speakers_file, "w") as f:
            json.dump(speakers_data, f)

        # Run validate command
        result = runner.invoke(
            cli,
            ["transcribe", "validate", "--output-dir", str(Path(tmpdir) / "transcriptions")],
        )

        assert result.exit_code == 0
        assert "All transcription files are valid!" in result.output
