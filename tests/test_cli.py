import builtins
import importlib.util
import json
import shutil
import sqlite3
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

# Expected database schema components
EXPECTED_TABLES = {
    "feeds",
    "feeds_extended",
    "episodes",
    "episodes_extended",
    "playlists",
    "chapters",
    "episode_downloads",
    "transcriptions",
    "transcription_segments",
}

EXPECTED_VIEWS = {
    "episodes_played",
    "episodes_deleted",
    "episodes_starred",
}


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


def test_config_check_detects_uninitialized_database(monkeypatch, tmp_path: Path) -> None:
    """Test that config check detects a database file that is not initialized."""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir(parents=True, exist_ok=True)

    # Create empty database file (not initialized)
    db_path = app_dir / "retrocast.db"
    db_path.touch()

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "check"])

    assert result.exit_code == 1
    assert "Not initialized" in result.output
    # Check for the action text (may be wrapped in table)
    assert "config" in result.output.lower() and "initialize" in result.output.lower()


def test_config_check_detects_initialized_database(monkeypatch, tmp_path: Path) -> None:
    """Test that config check detects a properly initialized database."""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir(parents=True, exist_ok=True)

    # Create and initialize database
    db_path = app_dir / "retrocast.db"
    from retrocast.datastore import Datastore

    Datastore(db_path)  # This initializes the schemas

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "check"])

    assert result.exit_code == 1  # Still incomplete due to missing auth
    assert "Initialized" in result.output
    assert "Not initialized" not in result.output


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


def test_config_location_db_path(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location", "--db-path"])

    assert result.exit_code == 0, result.output
    # Parse the JSON string output
    assert json.loads(result.stdout) == str(app_dir / "retrocast.db")


def test_config_location_app_dir(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location", "--app-dir"])

    assert result.exit_code == 0, result.output
    # Parse the JSON string output
    assert json.loads(result.stdout) == str(app_dir)


def test_config_location_mutual_exclusivity(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()

    # Test --format json with --db-path
    result = runner.invoke(cli, ["config", "location", "--format", "json", "--db-path"])
    assert result.exit_code != 0
    assert "only one output option" in result.output.lower()

    # Test --db-path with --app-dir
    result = runner.invoke(cli, ["config", "location", "--db-path", "--app-dir"])
    assert result.exit_code != 0
    assert "only one output option" in result.output.lower()

    # Test --format json with --app-dir
    result = runner.invoke(cli, ["config", "location", "--format", "json", "--app-dir"])
    assert result.exit_code != 0
    assert "only one output option" in result.output.lower()


def test_config_location_json_encoding(monkeypatch, tmp_path: Path) -> None:
    # Test with a path that contains special characters
    app_dir = tmp_path / "retrocast tests with spaces"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()

    # Test --db-path with special characters in path
    result = runner.invoke(cli, ["config", "location", "--db-path"])
    assert result.exit_code == 0, result.output
    # Verify JSON is properly encoded and parseable
    parsed = json.loads(result.stdout)
    assert parsed == str(app_dir / "retrocast.db")
    assert "retrocast tests with spaces" in parsed

    # Test --app-dir with special characters in path
    result = runner.invoke(cli, ["config", "location", "--app-dir"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.stdout)
    assert parsed == str(app_dir)
    assert "retrocast tests with spaces" in parsed


def test_meta_group_exposes_overcast_transcripts_help() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["meta", "overcast", "transcripts", "--help"])

    assert result.exit_code == 0
    assert "Download available transcripts" in result.output


def test_config_initialize_creates_database_with_schemas(monkeypatch, tmp_path: Path) -> None:
    """Test that config initialize creates database with all required schemas."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "initialize", "-y"])

    assert result.exit_code == 0, result.output
    assert app_dir.exists()

    # Check that database was created
    db_path = app_dir / "retrocast.db"
    assert db_path.exists()

    # Verify database has the expected tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall()}

    # Check that all expected tables exist
    for table in EXPECTED_TABLES:
        assert table in tables, f"Table '{table}' not found in database"

    # Check that views were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = {row[0] for row in cursor.fetchall()}

    for view in EXPECTED_VIEWS:
        assert view in views, f"View '{view}' not found in database"

    conn.close()

    # Verify output shows initialization success
    assert "Database schemas:" in result.output
    assert "Initialized" in result.output


def test_config_initialize_idempotent(monkeypatch, tmp_path: Path) -> None:
    """Test that config initialize can be run multiple times safely."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()

    # First initialization
    result1 = runner.invoke(cli, ["config", "initialize", "-y"])
    assert result1.exit_code == 0

    # Second initialization (should succeed without errors)
    result2 = runner.invoke(cli, ["config", "initialize", "-y"])
    assert result2.exit_code == 0

    # Database should still be valid
    db_path = app_dir / "retrocast.db"
    assert db_path.exists()


def test_sync_overcast_init_creates_database_with_schemas(monkeypatch, tmp_path: Path) -> None:
    """Test that sync overcast init creates database with all required schemas."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "overcast", "init"])

    assert result.exit_code == 0, result.output
    assert app_dir.exists()

    # Check that database was created
    db_path = app_dir / "retrocast.db"
    assert db_path.exists()

    # Verify database has the expected tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall()}

    # Check that all expected tables exist
    for table in EXPECTED_TABLES:
        assert table in tables, f"Table '{table}' not found in database"

    # Check that views were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = {row[0] for row in cursor.fetchall()}

    for view in EXPECTED_VIEWS:
        assert view in views, f"View '{view}' not found in database"

    conn.close()

    # Verify output shows initialization success
    assert "Overcast Database Initialization" in result.output
    assert "Created" in result.output or "Already exists" in result.output


def test_sync_overcast_init_idempotent(monkeypatch, tmp_path: Path) -> None:
    """Test that sync overcast init can be run multiple times safely."""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()

    # First initialization
    result1 = runner.invoke(cli, ["sync", "overcast", "init"])
    assert result1.exit_code == 0
    assert "Created" in result1.output

    # Second initialization (should succeed and report already exists)
    result2 = runner.invoke(cli, ["sync", "overcast", "init"])
    assert result2.exit_code == 0
    assert "Already exists" in result2.output

    # Database should still be valid
    db_path = app_dir / "retrocast.db"
    assert db_path.exists()
