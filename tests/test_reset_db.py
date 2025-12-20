import builtins
import importlib.util
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

from retrocast.cli import cli
from retrocast.datastore import Datastore


def test_reset_db_with_nonexistent_database(monkeypatch, tmp_path: Path) -> None:
    """Test reset-db command when database doesn't exist"""
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db"])

    assert result.exit_code == 0
    assert "does not exist" in result.output.lower()


def test_reset_db_dry_run(monkeypatch, tmp_path: Path) -> None:
    """Test reset-db with --dry-run flag"""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir()
    db_path = app_dir / "retrocast.db"

    # Create a database with schema
    datastore = Datastore(db_path)

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db", "--dry-run"])

    assert result.exit_code == 0
    assert "dry run" in result.output.lower()
    assert "no changes" in result.output.lower()
    assert "tables" in result.output.lower()
    assert "views" in result.output.lower()

    # Verify database still exists and has tables
    assert db_path.exists()
    datastore = Datastore(db_path)
    schema_info = datastore.get_schema_info()
    assert len(schema_info["tables"]) > 0


def test_reset_db_with_confirmation_no(monkeypatch, tmp_path: Path) -> None:
    """Test reset-db command with user declining confirmation"""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir()
    db_path = app_dir / "retrocast.db"

    # Create a database with schema
    datastore = Datastore(db_path)

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db"], input="n\n")

    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()

    # Verify database still exists and has tables
    assert db_path.exists()
    datastore = Datastore(db_path)
    schema_info = datastore.get_schema_info()
    assert len(schema_info["tables"]) > 0


def test_reset_db_with_confirmation_yes(monkeypatch, tmp_path: Path) -> None:
    """Test reset-db command with user confirming"""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir()
    db_path = app_dir / "retrocast.db"

    # Create a database with schema and add some data
    datastore = Datastore(db_path)
    datastore.save_feed_and_episodes(
        {"overcastId": 1, "title": "Test Feed", "subscribed": True, "xmlUrl": "http://test.com/feed"},
        [{"overcastId": 1, "feedId": 1, "title": "Test Episode", "url": "http://test.com/episode"}]
    )

    # Verify data exists
    conn = datastore._connection()
    count_before = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
    assert count_before > 0

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db"], input="y\n")

    assert result.exit_code == 0
    assert "successfully" in result.output.lower()

    # Verify database still exists but is empty
    assert db_path.exists()
    datastore = Datastore(db_path)
    schema_info = datastore.get_schema_info()
    assert len(schema_info["tables"]) > 0  # Schema recreated

    # Verify data is gone
    conn = datastore._connection()
    count_after = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
    assert count_after == 0


def test_reset_db_with_yes_flag(monkeypatch, tmp_path: Path) -> None:
    """Test reset-db command with -y flag to skip confirmation"""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir()
    db_path = app_dir / "retrocast.db"

    # Create a database with schema
    datastore = Datastore(db_path)

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db", "-y"])

    assert result.exit_code == 0
    assert "successfully" in result.output.lower()

    # Verify database still exists with schema
    assert db_path.exists()
    datastore = Datastore(db_path)
    schema_info = datastore.get_schema_info()
    assert len(schema_info["tables"]) > 0


def test_reset_db_recreates_all_tables(monkeypatch, tmp_path: Path) -> None:
    """Test that reset-db recreates all expected tables"""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir()
    db_path = app_dir / "retrocast.db"

    # Create initial database
    datastore = Datastore(db_path)
    schema_before = datastore.get_schema_info()
    tables_before = set(schema_before["tables"])
    views_before = set(schema_before["views"])

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db", "-y"])

    assert result.exit_code == 0

    # Verify schema recreated with same structure
    datastore = Datastore(db_path)
    schema_after = datastore.get_schema_info()
    tables_after = set(schema_after["tables"])
    views_after = set(schema_after["views"])

    # All tables should be recreated
    assert tables_before == tables_after
    assert views_before == views_after

    # Verify key tables exist
    expected_tables = {
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
    assert expected_tables.issubset(tables_after)

    # Verify views exist
    expected_views = {
        "episodes_played",
        "episodes_deleted",
        "episodes_starred",
    }
    assert expected_views.issubset(views_after)


def test_reset_db_dry_run_shows_correct_counts(monkeypatch, tmp_path: Path) -> None:
    """Test that dry-run mode shows accurate counts"""
    app_dir = tmp_path / "retrocast-tests"
    app_dir.mkdir()
    db_path = app_dir / "retrocast.db"

    # Create a database
    datastore = Datastore(db_path)
    schema_info = datastore.get_schema_info()

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "reset-db", "--dry-run"])

    assert result.exit_code == 0

    # Check that counts are displayed
    assert str(len(schema_info["tables"])) in result.output
    assert str(len(schema_info["views"])) in result.output
