import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner
from loguru import logger

from retrocast import podcast_archiver_attach as attach
from retrocast.cli import cli


def _prepare_databases(tmp_path: Path) -> tuple[Path, Path]:
    main_db = tmp_path / "retrocast.db"
    with sqlite3.connect(main_db) as conn:
        conn.execute("create table base(id integer)")

    archiver_db = tmp_path / "episodes.db"
    with sqlite3.connect(archiver_db) as conn:
        conn.execute("create table episodes(id integer primary key, title text)")
        conn.execute("insert into episodes(id, title) values (1, 'hello')")

    return main_db, archiver_db


def test_sql_query_attaches_podcast_archiver(monkeypatch, tmp_path: Path) -> None:
    main_db, archiver_db = _prepare_databases(tmp_path)
    monkeypatch.setattr(attach, "get_podcast_archiver_db_path", lambda: archiver_db)
    monkeypatch.setattr("retrocast.cli.setup_logging", lambda *_, **__: logger.remove())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "query",
            "--database",
            str(main_db),
            "query",
            "select title from podcast_archiver.episodes order by id",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [{"title": "hello"}]


def test_sql_rows_supports_podcast_archiver_tables(monkeypatch, tmp_path: Path) -> None:
    main_db, archiver_db = _prepare_databases(tmp_path)
    monkeypatch.setattr(attach, "get_podcast_archiver_db_path", lambda: archiver_db)
    monkeypatch.setattr("retrocast.cli.setup_logging", lambda *_, **__: logger.remove())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "query",
            "--database",
            str(main_db),
            "rows",
            "podcast_archiver.episodes",
            "--nl",
        ],
    )

    assert result.exit_code == 0, result.output
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert rows == [{"id": 1, "title": "hello"}]
