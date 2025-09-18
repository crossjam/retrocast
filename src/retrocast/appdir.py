"""Application directory management for retrocast."""

from pathlib import Path

import platformdirs


def get_app_dir() -> Path:
    """Get the application directory for retrocast.

    Creates the directory if it doesn't exist.

    Returns:
        Path: The application directory path
    """
    app_dir = Path(platformdirs.user_data_dir("net.memexponent.retrocast", "retrocast"))
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_auth_path() -> Path:
    """Get the path to the auth.json file in the application directory.

    Returns:
        Path: The path to the auth.json file
    """
    return get_app_dir() / "auth.json"


def get_default_db_path() -> Path:
    """Get the default path to the database file in the application directory.

    Returns:
        Path: The path to the database file
    """
    return get_app_dir() / "retrocast.db"
