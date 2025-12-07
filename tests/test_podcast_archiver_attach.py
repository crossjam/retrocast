import sqlite3
from pathlib import Path

import platformdirs
from podcast_archiver import constants as podcast_archiver_constants

from retrocast import podcast_archiver_attach as attach


def test_get_podcast_archiver_db_path_prefers_appdir(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "appdir"
    app_dir.mkdir()
    episodes_db = app_dir / attach.APPDIR_ARCHIVER_DB
    episodes_db.touch()

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.yaml"
    config_path.touch()
    archiver_default = config_dir / podcast_archiver_constants.DEFAULT_DATABASE_FILENAME
    archiver_default.touch()

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))
    monkeypatch.setattr(attach, "get_default_config_path", lambda: config_path)

    resolved_path = attach.get_podcast_archiver_db_path()

    assert resolved_path == episodes_db.resolve()

    episodes_db.unlink()
    fallback_path = attach.get_podcast_archiver_db_path()

    assert fallback_path == archiver_default.resolve()


def test_get_podcast_archiver_db_path_returns_none_when_missing(
    monkeypatch, tmp_path: Path
) -> None:
    app_dir = tmp_path / "appdir"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.yaml"
    config_path.touch()

    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))
    monkeypatch.setattr(attach, "get_default_config_path", lambda: config_path)

    assert attach.get_podcast_archiver_db_path() is None


def test_attach_podcast_archiver_handles_alias_collision(monkeypatch, tmp_path: Path) -> None:
    attached_db = tmp_path / "archiver.sqlite"
    with sqlite3.connect(attached_db) as conn:
        conn.execute("create table episodes (id integer)")
        conn.execute("create view episode_view as select id from episodes")

    existing_db = tmp_path / "existing.sqlite"
    with sqlite3.connect(existing_db) as conn:
        conn.execute("create table placeholder (id integer)")

    conn = sqlite3.connect(":memory:")
    conn.execute("create table episodes (id integer)")
    conn.execute("attach database ? as podcast_archiver", (str(existing_db),))

    monkeypatch.setattr(attach, "get_podcast_archiver_db_path", lambda: attached_db)

    attached = attach.attach_podcast_archiver(conn)

    assert attached is not None
    assert attached.alias == "podcast_archiver_1"
    assert attached.path == attached_db.resolve()
    assert attached.tables == ("episodes",)
    assert attached.views == ("episode_view",)
    assert attached.colliding_objects == ("episodes",)
