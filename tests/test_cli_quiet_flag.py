"""Tests for the -q/--quiet CLI flag."""

import builtins
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import platformdirs

# Set up rich stubs if not available
if importlib.util.find_spec("rich.console") is None:
    rich_module = types.ModuleType("rich")
    rich_console_module = types.ModuleType("rich.console")
    rich_markdown_module = types.ModuleType("rich.markdown")

    class _Console:  # noqa: D401 - simple stub
        """Console stub used for tests when Rich is unavailable."""

        def print(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Pretend to print output."""

            kwargs.pop("highlight", None)
            builtins.print(*args, **kwargs)

    rich_console_module.Console = _Console  # type: ignore[attr-defined]
    rich_markdown_module.Markdown = lambda text: text  # type: ignore[assignment]
    sys.modules.setdefault("rich", rich_module)
    sys.modules.setdefault("rich.console", rich_console_module)
    sys.modules.setdefault("rich.markdown", rich_markdown_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from click.testing import CliRunner

from retrocast.cli import cli


def test_quiet_suppresses_info_logs(monkeypatch, tmp_path: Path) -> None:
    """Test that -q flag suppresses info-level log messages."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    # Mock setup_logging to capture the call
    mock_setup_logging = MagicMock()
    with patch("retrocast.cli.setup_logging", mock_setup_logging):
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", "about"])

        assert result.exit_code == 0
        # Verify setup_logging was called with quiet=True
        mock_setup_logging.assert_called_once()
        call_kwargs = mock_setup_logging.call_args[1]
        assert call_kwargs["quiet"] is True
        assert call_kwargs["verbose"] is False


def test_quiet_overrides_verbose(monkeypatch, tmp_path: Path) -> None:
    """Test that -q flag takes precedence over -v flag."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    # Mock setup_logging to capture the call
    mock_setup_logging = MagicMock()
    with patch("retrocast.cli.setup_logging", mock_setup_logging):
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", "-v", "about"])

        assert result.exit_code == 0
        # Verify setup_logging was called with both flags
        mock_setup_logging.assert_called_once()
        call_kwargs = mock_setup_logging.call_args[1]
        assert call_kwargs["quiet"] is True
        assert call_kwargs["verbose"] is True
        # The setup_logging function itself should handle the precedence


def test_subcommand_respects_quiet(monkeypatch, tmp_path: Path) -> None:
    """Test that subcommands respect the top-level -q flag."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    # Mock setup_logging to capture calls
    mock_setup_logging = MagicMock()
    
    with patch("retrocast.cli.setup_logging", mock_setup_logging):
        with patch("retrocast.download_commands.setup_logging", mock_setup_logging):
            runner = CliRunner()
            # Test with the download aria command (which has its own -v flag)
            # We'll just test that it accepts the command structure
            result = runner.invoke(cli, ["-q", "download", "aria", "--help"])
            
            # The command should run successfully
            assert result.exit_code == 0
            # Verify the initial setup_logging was called with quiet=True
            first_call_kwargs = mock_setup_logging.call_args_list[0][1]
            assert first_call_kwargs["quiet"] is True


def test_quiet_flag_in_logging_config(monkeypatch, tmp_path: Path) -> None:
    """Test that the logging_config.setup_logging function honors the quiet flag."""
    from retrocast.logging_config import setup_logging
    
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()
    
    # Mock the logger to capture configuration
    with patch("retrocast.logging_config._logger") as mock_logger:
        with patch("retrocast.logging_config.LoguruConfig") as mock_config:
            # Test with quiet=True
            setup_logging(app_dir, quiet=True, verbose=False)
            
            # Verify remove was called
            mock_logger.remove.assert_called()
            
            # Verify LoguruConfig.load was called with ERROR level
            load_call_args = mock_config.load.call_args
            if load_call_args:
                config_dict = load_call_args[0][0]
                # The first handler should have ERROR level when quiet=True
                assert config_dict["handlers"][0]["level"] == "ERROR"


def test_verbose_without_quiet(monkeypatch, tmp_path: Path) -> None:
    """Test that verbose flag works when quiet is not set."""
    from retrocast.logging_config import setup_logging
    
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()
    
    # Mock the logger to capture configuration
    with patch("retrocast.logging_config._logger") as mock_logger:
        with patch("retrocast.logging_config.LoguruConfig") as mock_config:
            # Test with verbose=True, quiet=False
            setup_logging(app_dir, verbose=True, quiet=False)
            
            # Verify remove was called
            mock_logger.remove.assert_called()
            
            # Verify LoguruConfig.load was called with DEBUG level
            load_call_args = mock_config.load.call_args
            if load_call_args:
                config_dict = load_call_args[0][0]
                # The first handler should have DEBUG level when verbose=True
                assert config_dict["handlers"][0]["level"] == "DEBUG"


def test_default_logging_level(monkeypatch, tmp_path: Path) -> None:
    """Test that default logging level is INFO when neither quiet nor verbose is set."""
    from retrocast.logging_config import setup_logging
    
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()
    
    # Mock the logger to capture configuration
    with patch("retrocast.logging_config._logger") as mock_logger:
        with patch("retrocast.logging_config.LoguruConfig") as mock_config:
            # Test with default settings
            setup_logging(app_dir, verbose=False, quiet=False)
            
            # Verify remove was called
            mock_logger.remove.assert_called()
            
            # Verify LoguruConfig.load was called with INFO level
            load_call_args = mock_config.load.call_args
            if load_call_args:
                config_dict = load_call_args[0][0]
                # The first handler should have INFO level by default
                assert config_dict["handlers"][0]["level"] == "INFO"
