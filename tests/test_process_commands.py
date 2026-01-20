"""Tests for transcription commands (transcription CLI)."""


import pytest
from click.testing import CliRunner

from retrocast.cli import cli


class TestTranscriptionCommands:
    """Tests for transcription command group."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_transcription_help(self, runner):
        """Test transcription command help."""
        result = runner.invoke(cli, ["transcription", "--help"])
        assert result.exit_code == 0
        assert "Manage audio transcriptions" in result.output
        assert "process" in result.output
        assert "backends" in result.output

    def test_list_backends(self, runner):
        """Test backends list command."""
        result = runner.invoke(cli, ["transcription", "backends", "list"])
        assert result.exit_code == 0
        assert "Backend" in result.output
        assert "mlx-whisper" in result.output

    def test_test_backend_unknown(self, runner):
        """Test backends test with unknown backend."""
        result = runner.invoke(cli, ["transcription", "backends", "test", "nonexistent"])
        assert result.exit_code == 0
        assert "Unknown backend" in result.output

    def test_test_backend_mlx(self, runner):
        """Test backends test with MLX backend."""
        result = runner.invoke(cli, ["transcription", "backends", "test", "mlx-whisper"])
        assert result.exit_code == 0
        assert "mlx-whisper" in result.output
        # Should show not available on non-macOS or without mlx_whisper installed
        assert ("not available" in result.output.lower()) or (
            "available and ready" in result.output.lower()
        )

    def test_process_no_paths(self, runner):
        """Test process command with no paths."""
        result = runner.invoke(cli, ["transcription", "process"])
        assert result.exit_code != 0
        # Should error because no paths provided

    def test_process_help(self, runner):
        """Test process command help."""
        result = runner.invoke(cli, ["transcription", "process", "--help"])
        assert result.exit_code == 0
        assert "Process audio files" in result.output
        assert "--backend" in result.output
        assert "--model" in result.output
        assert "--format" in result.output

    def test_search_help(self, runner):
        """Test search command help."""
        result = runner.invoke(cli, ["transcription", "search", "--help"])
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
        result = runner.invoke(cli, ["transcription", "search"])
        assert result.exit_code != 0
        # Should error because query is required

    def test_search_no_database(self, runner):
        """Test search command with non-existent/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["transcription", "search", "test", "--db", "nonexistent.db"]
            )
            # Should succeed but find no results (empty database created)
            assert result.exit_code == 0
            assert "No results found" in result.output

    def test_summary_help(self, runner):
        """Test summary command help."""
        result = runner.invoke(cli, ["transcription", "summary", "--help"])
        assert result.exit_code == 0
        assert "Display overall transcription statistics" in result.output

    def test_summary_no_database(self, runner):
        """Test summary command with new/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["transcription", "summary", "--db", "test.db"]
            )
            # Should succeed but show no transcriptions message
            assert result.exit_code == 0
            assert "No transcriptions found" in result.output

    def test_podcasts_list_help(self, runner):
        """Test podcasts list command help."""
        result = runner.invoke(cli, ["transcription", "podcasts", "list", "--help"])
        assert result.exit_code == 0
        assert "List all podcasts with transcriptions" in result.output
        assert "--limit" in result.output

    def test_podcasts_list_no_database(self, runner):
        """Test podcasts list with new/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["transcription", "podcasts", "list", "--db", "test.db"]
            )
            assert result.exit_code == 0
            assert "No transcriptions found" in result.output

    def test_podcasts_summary_help(self, runner):
        """Test podcasts summary command help."""
        result = runner.invoke(cli, ["transcription", "podcasts", "summary", "--help"])
        assert result.exit_code == 0
        assert "Show summary statistics for podcasts" in result.output

    def test_podcasts_summary_no_database(self, runner):
        """Test podcasts summary with new/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["transcription", "podcasts", "summary", "--db", "test.db"]
            )
            assert result.exit_code == 0
            assert "No transcriptions found" in result.output

    def test_episodes_list_help(self, runner):
        """Test episodes list command help."""
        result = runner.invoke(cli, ["transcription", "episodes", "list", "--help"])
        assert result.exit_code == 0
        assert "List transcribed episodes" in result.output
        assert "--podcast" in result.output
        assert "--limit" in result.output
        assert "--page" in result.output
        assert "--order" in result.output

    def test_episodes_list_no_database(self, runner):
        """Test episodes list with new/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["transcription", "episodes", "list", "--db", "test.db"]
            )
            assert result.exit_code == 0
            assert "No transcriptions found" in result.output

    def test_episodes_summary_help(self, runner):
        """Test episodes summary command help."""
        result = runner.invoke(cli, ["transcription", "episodes", "summary", "--help"])
        assert result.exit_code == 0
        assert "Show summary statistics for transcribed episodes" in result.output
        assert "--podcast" in result.output

    def test_episodes_summary_no_database(self, runner):
        """Test episodes summary with new/empty database."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["transcription", "episodes", "summary", "--db", "test.db"]
            )
            assert result.exit_code == 0
            assert "No transcriptions found" in result.output
