"""Application directory management for retrocast."""

from pathlib import Path

import platformdirs
from rich.console import Console

console = Console()


def get_app_dir(*, create: bool = False) -> Path:
    """Get the application directory for retrocast.

    Args:
        create: Whether to create the directory if it does not exist.

    Returns:
        Path: The application directory path
    """

    app_dir = Path(platformdirs.user_data_dir("net.memexponent.retrocast", "retrocast"))
    if create and not app_dir.exists():
        console.print(f"[bold green]Creating application directory:[/] [blue]{app_dir}[/]")
        app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def ensure_app_dir() -> Path:
    """Ensure the application directory exists and return the path."""

    return get_app_dir(create=True)


def get_auth_path(*, create: bool = False) -> Path:
    """Get the path to the auth.json file in the application directory.

    Args:
        create: Whether to create the directory if it does not exist.

    Returns:
        Path: The path to the auth.json file
    """

    return get_app_dir(create=create) / "auth.json"


def get_default_db_path(*, create: bool = False) -> Path:
    """Get the default path to the database file in the application directory.

    Args:
        create: Whether to create the directory if it does not exist.

    Returns:
        Path: The path to the database file
    """

    return get_app_dir(create=create) / "retrocast.db"
