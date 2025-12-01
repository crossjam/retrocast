import builtins
import importlib.util
import shutil
import sys
import tempfile
import types
from pathlib import Path

try:
    import platformdirs  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for test envs without dependency
    platformdirs = types.ModuleType("platformdirs")

    def _user_data_dir(app_name: str, app_author: str) -> str:  # noqa: ARG001 - signature per library
        return str(Path(tempfile.gettempdir()) / "retrocast-tests")

    platformdirs.user_data_dir = _user_data_dir  # type: ignore[attr-defined]
    sys.modules["platformdirs"] = platformdirs

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

from retrocast.about_content import load_about_markdown
from retrocast.cli import cli


def _first_markdown_heading(markdown_text: str) -> str:
    return next(line for line in markdown_text.splitlines() if line.strip()).lstrip("# ").strip()


ABOUT_HEADING = _first_markdown_heading(load_about_markdown())


def test_cli_default_runs_about() -> None:
    runner = CliRunner()

    result = runner.invoke(cli)

    assert result.exit_code == 0
    assert ABOUT_HEADING in result.output


def test_cli_about_command_explicit() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["about"])

    assert result.exit_code == 0
    assert ABOUT_HEADING in result.output


def test_config_check_reports_missing_without_creating(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))
    if app_dir.exists():
        shutil.rmtree(app_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "check"])

    assert result.exit_code == 1
    assert "Retrocast Configuration" in result.output
    assert not app_dir.exists()


def test_retrieve_group_exposes_overcast_transcripts_help() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["retrieve", "overcast", "transcripts", "--help"])

    assert result.exit_code == 0
    assert "Download available transcripts" in result.output
