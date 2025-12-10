import builtins
import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path

import platformdirs

if importlib.util.find_spec("rich.console") is None:
    rich_module = types.ModuleType("rich")
    rich_console_module = types.ModuleType("rich.console")
    rich_markdown_module = types.ModuleType("rich.markdown")

    class _Console:  # noqa: D401 - simple stub
        """Console stub used for tests when Rich is unavailable."""

        def print(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Pretend to print output."""

            kwargs.pop("highlight", None)
            # type: ignore used because we're intentionally passing through kwargs
            builtins.print(*args, **kwargs)  # type: ignore[misc]

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
    assert "retrocast configuration" in result.output.lower()
    assert not app_dir.exists()


def test_config_location_json(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location", "--format", "json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "app_dir": str(app_dir),
        "auth_path": str(app_dir / "auth.json"),
        "db_path": str(app_dir / "retrocast.db"),
    }


def test_config_location_missing(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location"])

    assert result.exit_code == 1
    assert "configuration locations" in result.output.lower()
    assert "missing" in result.output.lower()
    assert not app_dir.exists()


def test_config_location_ready(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    auth_path = app_dir / "auth.json"
    db_path = app_dir / "retrocast.db"
    app_dir.mkdir()
    auth_path.touch()
    db_path.touch()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location"])

    assert result.exit_code == 0, result.output
    assert "configuration ready" in result.output.lower()
    assert "missing" not in result.output.lower()


def test_meta_group_exposes_overcast_transcripts_help() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["meta", "overcast", "transcripts", "--help"])

    assert result.exit_code == 0
    assert "Download available transcripts" in result.output
