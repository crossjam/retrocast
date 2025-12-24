"""Tests for process commands (transcription CLI)."""


import pytest
from click.testing import CliRunner

from retrocast.cli import cli


class TestProcessCommands:
    """Tests for process command group."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_process_help(self, runner):
        """Test process command help."""
        result = runner.invoke(cli, ["process", "--help"])
        assert result.exit_code == 0
        assert "Process podcast audio files" in result.output
        assert "transcribe" in result.output
        assert "backends" in result.output

    def test_list_backends(self, runner):
        """Test backends list command."""
        result = runner.invoke(cli, ["process", "backends", "list"])
        assert result.exit_code == 0
        assert "Backend" in result.output
        assert "mlx-whisper" in result.output

    def test_test_backend_unknown(self, runner):
        """Test backends test with unknown backend."""
        result = runner.invoke(cli, ["process", "backends", "test", "nonexistent"])
        assert result.exit_code == 0
        assert "Unknown backend" in result.output

    def test_test_backend_mlx(self, runner):
        """Test backends test with MLX backend."""
        result = runner.invoke(cli, ["process", "backends", "test", "mlx-whisper"])
        assert result.exit_code == 0
        assert "mlx-whisper" in result.output
        # Should show not available on non-macOS or without mlx_whisper installed
        assert ("not available" in result.output.lower()) or (
            "available and ready" in result.output.lower()
        )

    def test_transcribe_no_paths(self, runner):
        """Test transcribe command with no paths."""
        result = runner.invoke(cli, ["process", "transcribe"])
        assert result.exit_code != 0
        # Should error because no paths provided

    def test_transcribe_help(self, runner):
        """Test transcribe command help."""
        result = runner.invoke(cli, ["process", "transcribe", "--help"])
        assert result.exit_code == 0
        assert "Transcribe audio files" in result.output
        assert "--backend" in result.output
        assert "--model" in result.output
        assert "--format" in result.output

    def test_search_help(self, runner):
        """Test search command help."""
        result = runner.invoke(cli, ["process", "search", "--help"])
        assert result.exit_code == 0
        assert "Search transcribed podcast content" in result.output
        assert "--podcast" in result.output
        assert "--speaker" in result.output
        assert "--backend" in result.output
        assert "--model" in result.output
        assert "--date-from" in result.output
        assert "--date-to" in result.output
        assert "--limit" in result.output
        assert "--page" in result.output
        assert "--context" in result.output
        assert "--export" in result.output

    def test_search_no_query(self, runner):
        """Test search command with no query."""
        result = runner.invoke(cli, ["process", "search"])
        assert result.exit_code != 0
        # Should error because query is required

    def test_search_no_database(self, runner):
        """Test search command with non-existent/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["process", "search", "test", "--db", "nonexistent.db"]
            )
            # Should succeed but find no results (empty database created)
            assert result.exit_code == 0
            assert "No results found" in result.output
