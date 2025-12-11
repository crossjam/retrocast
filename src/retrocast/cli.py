#!/usr/bin/env python

import enum
import json
import sys
import tarfile
from contextlib import nullcontext
from pathlib import Path
from typing import BinaryIO, ContextManager, cast

import click
import rich_click
from click.core import ParameterSource
from click_default_group import DefaultGroup
from loguru import logger
from podcast_archiver.cli import main as podcast_archiver_command
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from retrocast.about_content import load_about_markdown
from retrocast.appdir import (
    ensure_app_dir,
    get_app_dir,
    get_auth_path,
    get_default_db_path,
)
from retrocast.download_commands import download
from retrocast.episode_db_commands import episode_db
from retrocast.logging_config import setup_logging
from retrocast.overcast import chapters, overcast, transcripts

from . import sql_cli

_podcast_archiver_attached = False


@click.group(cls=DefaultGroup, default="about", default_if_no_args=True)
@click.version_option()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging output.")
@click.option("-q", "--quiet", is_flag=True, help="Enable quiet mode (ERROR level logging only).")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Save listening history and feed/episode info from Overcast to SQLite."""
    global _podcast_archiver_attached

    # Initialize context object if it doesn't exist
    ctx.ensure_object(dict)
    # Store app directory in context
    app_dir = get_app_dir(create=False)
    ctx.obj["app_dir"] = app_dir
    log_file = app_dir / "retrocast.log"
    ctx.obj["log_file"] = log_file
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    setup_logging(
        app_dir,
        verbose=verbose,
        quiet=quiet,
        log_file=log_file,
        enable_file_logging=app_dir.exists(),
    )

    # Attach podcast archiver commands after logging is configured
    if not _podcast_archiver_attached:
        _attach_podcast_archiver_passthroughs(cast(DefaultGroup, ctx.command))
        _podcast_archiver_attached = True


@cli.command()
def about() -> None:
    """Display information about retrocast"""
    console = Console()

    try:
        about_text = load_about_markdown()
    except (FileNotFoundError, OSError):
        console.print("[bold red]Unable to load retrocast about information.[/bold red]")
        return

    console.print(Markdown(about_text))


@cli.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage the retrocast configuration data"""


@config.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Report configuration status without making changes"""

    console = Console()
    app_dir = get_app_dir(create=False)
    auth_path = get_auth_path(create=False)
    db_path = get_default_db_path(create=False)

    app_exists = app_dir.exists()
    auth_exists = auth_path.exists() if app_exists else False
    db_exists = db_path.exists() if app_exists else False

    table = Table(
        title="retrocast Configuration",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Component", style="bold")
    table.add_column("Path", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Action", style="dim italic")

    table.add_row(
        "App Directory",
        str(app_dir),
        "[green]✓ Found[/green]" if app_exists else "[red]✗ Missing[/red]",
        "" if app_exists else "Run: retrocast config initialize",
    )

    if app_exists:
        table.add_row(
            "Auth File",
            str(auth_path),
            "[green]✓ Found[/green]" if auth_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast sync overcast auth" if not auth_exists else "",
        )
        table.add_row(
            "Database",
            str(db_path),
            "[green]✓ Found[/green]" if db_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast sync overcast save" if not db_exists else "",
        )
    else:
        table.add_row("Auth File", str(auth_path), "[dim]n/a[/dim]", "Initialize app directory")
        table.add_row("Database", str(db_path), "[dim]n/a[/dim]", "Initialize app directory")

    console.print()
    console.print(table)
    console.print()

    if app_exists and auth_exists and db_exists:
        console.print("[bold green]✓ Configuration ready[/bold green]")
        ctx.exit(0)
    console.print("[yellow]Setup incomplete; see suggested actions above.[/yellow]")
    ctx.exit(1)


@config.command(name="initialize")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Create the directory without confirmation prompts.",
)
@click.pass_context
def config_initialize(ctx: click.Context, yes: bool) -> None:
    """Create the retrocast configuration directory"""

    console = Console()
    app_dir = get_app_dir(create=False)

    if app_dir.exists() and not yes:
        if not click.confirm(
            f"Configuration directory already exists at {app_dir}. Continue?",
            default=False,
        ):
            console.print("[yellow]Initialization cancelled.[/yellow]")
            ctx.exit(1)

    app_dir = ensure_app_dir()
    setup_logging(
        app_dir,
        verbose=ctx.obj.get("verbose", False),
        quiet=ctx.obj.get("quiet", False),
        log_file=ctx.obj.get("log_file"),
        enable_file_logging=True,
    )

    console.print()
    console.print("[bold cyan]retrocast Initialization[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")
    table.add_row("Config directory:", str(app_dir))
    table.add_row("Auth path:", str(get_auth_path(create=True)))
    table.add_row("Database path:", str(get_default_db_path(create=True)))

    console.print(table)
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Authenticate: [cyan]retrocast sync overcast auth[/cyan]")
    console.print("  2. Sync data:    [cyan]retrocast sync overcast save[/cyan]")
    console.print("  3. Download:     [cyan]retrocast meta overcast transcripts[/cyan]")
    console.print()


@config.command()
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, allow_dash=False, path_type=Path),
    help="Destination for the gzipped archive. Writes to stdout when omitted.",
)
@click.option(
    "-c",
    "--compression-level",
    type=click.IntRange(0, 9),
    default=6,
    show_default=True,
    help="Gzip compression level (0-9).",
)
@click.option("-f", "--force", is_flag=True, help="Overwrite the output archive if it exists.")
@click.pass_context
def archive(
    ctx: click.Context,
    output_path: Path | None,
    compression_level: int,
    force: bool,
) -> None:
    """Archive the configuration directory as a gzipped tarball"""

    console = Console(stderr=True)
    app_dir = get_app_dir(create=False)

    if not app_dir.exists():
        console.print("[red]Configuration directory not found. Initialize it first.[/red]")
        ctx.exit(1)

    stream: BinaryIO = sys.stdout.buffer
    stream_context: ContextManager[BinaryIO] = nullcontext[BinaryIO](stream)

    if output_path is not None:
        if output_path.exists() and not force:
            if not click.confirm(
                f"Overwrite existing archive at {output_path}?",
                default=False,
            ):
                console.print("[yellow]Archive cancelled.[/yellow]")
                ctx.exit(1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stream_context = cast(ContextManager[BinaryIO], output_path.open("wb"))

    with stream_context as file_obj:
        with tarfile.open(
            fileobj=file_obj,
            mode="w:gz",
            compresslevel=compression_level,
        ) as tar:
            tar.add(app_dir, arcname=app_dir.name)

    if output_path is not None:
        console.print(f"[green]Archive written to {output_path}[/green]")


class LocationOutput(enum.Enum):
    CONSOLE = enum.auto()
    JSON = enum.auto()


@config.command()
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(LocationOutput, case_sensitive=False),
    default=LocationOutput.CONSOLE,
)
@click.pass_context
def location(ctx: click.Context, output_format) -> None:
    """Output the location of the configuration directory"""

    console = Console()
    app_dir = get_app_dir(create=False)
    auth_path = get_auth_path(create=False)
    db_path = get_default_db_path(create=False)

    app_exists = app_dir.exists()
    auth_exists = auth_path.exists() if app_exists else False
    db_exists = db_path.exists() if app_exists else False

    if output_format == LocationOutput.JSON:
        res = {
            "app_dir": str(app_dir),
            "auth_path": str(auth_path),
            "db_path": str(db_path),
        }

        json.dump(res, fp=sys.stdout)
        ctx.exit(0)

    table = Table(
        title="retrocast Configuration Locations",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Component", style="bold")
    table.add_column("Path", style="dim")
    table.add_column("Status", justify="center")

    table.add_row(
        "App Directory",
        str(app_dir),
        "[green]✓ Found[/green]" if app_exists else "[red]✗ Missing[/red]",
        "" if app_exists else "Run: retrocast config initialize",
    )

    if app_exists:
        table.add_row(
            "Auth File",
            str(auth_path),
            "[green]✓ Found[/green]" if auth_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast sync overcast auth" if not auth_exists else "",
        )
        table.add_row(
            "Database",
            str(db_path),
            "[green]✓ Found[/green]" if db_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast sync overcast save" if not db_exists else "",
        )
    else:
        table.add_row("Auth File", str(auth_path), "[dim]n/a[/dim]", "Initialize app directory")
        table.add_row("Database", str(db_path), "[dim]n/a[/dim]", "Initialize app directory")

    console.print()
    console.print(table)
    console.print()

    if app_exists and auth_exists and db_exists:
        console.print("[bold green]✓ Configuration ready[/bold green]")
        ctx.exit(0)
    console.print("[yellow]Setup incomplete; see suggested actions above.[/yellow]")
    ctx.exit(1)


@cli.group()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Synchronize subscription metadata"""
    pass


@cli.group()
@click.pass_context
def meta(ctx: click.Context) -> None:
    """Download episode metadata and derived information"""
    pass


def _attach_podcast_archiver_passthroughs(main_group: DefaultGroup) -> None:
    download_command = main_group.commands.get("download")

    if not download_command:
        logger.warning("Could not find 'download' subcommand for podcast_archiver passthrough")
        return

    # Type assertion: self_command is a Group (has commands and add_command)
    download_command = cast("click.Group", download_command)

    wrapped_context_settings = podcast_archiver_command.context_settings
    wrapped_context_settings["ignore_unknown_options"] = True
    wrapped_context_settings["allow_extra_args"] = True
    logger.debug(f"Wrapped context settings: {wrapped_context_settings}")

    @download_command.command(
        name="podcast-archiver",
        help=podcast_archiver_command.help,
        context_settings=wrapped_context_settings,
    )
    @rich_click.pass_context
    def archiver_wrapped(ctx: rich_click.RichContext, force_download: bool = False, **kwargs):
        from pathlib import Path

        app_dir = get_app_dir()
        config_file = (app_dir / "podcast_archiver.yaml") if app_dir else None
        database_path = (app_dir / "episodes.db") if app_dir else None
        download_path = (app_dir / "episode_downloads") if app_dir else None

        logger.debug(
            f"Attached app dir, config file, db: {app_dir}, {config_file}, {database_path}"
        )

        if not ctx.params.get("database"):
            logger.info(f"Using app dir database parameter: {str(database_path)}")
            ctx.params["database"] = database_path

        param_source = ctx.get_parameter_source("archive_directory")
        logger.info(
            f"archive directory option source, defaulted: {param_source}"
            f", {param_source in (ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP)}"
        )

        if not ctx.params.get("archive_directory") or (
            param_source in (ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP)
        ):
            logger.info(f"Using app dir download dir parameter: {str(download_path)}")
            ctx.params["dir"] = download_path
            ctx.params["archive_directory"] = download_path

        logger.debug(f"ctx.args: {ctx.args}")
        logger.debug(f"ctx.params (before modification): {ctx.params}")

        if not ctx.params["archive_directory"].exists():
            logger.info(f"Ensuring download dir exists: {ctx.params['archive_directory']}\n")
            ctx.params["archive_directory"].mkdir(exist_ok=True)
        else:
            logger.info(f"Download dir exists: {ctx.params['archive_directory']}")

        # Handle --force-download: prompt and enable ignore_database
        if force_download:
            archive_dir = Path(ctx.params["archive_directory"])
            if archive_dir.exists():
                # Count existing media files
                media_extensions = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"}
                existing_files = [
                    f
                    for f in archive_dir.rglob("*")
                    if f.is_file() and f.suffix.lower() in media_extensions
                ]
                if existing_files:
                    Console(stderr=True).print(
                        f"\n[bold red]⚠️  WARNING: Force download is enabled![/bold red]\n"
                        f"This will DELETE {len(existing_files)} existing episode file(s) "
                        f"in [cyan]{archive_dir}[/cyan]\n"
                        f"before re-downloading them.\n"
                    )
                    if not click.confirm(
                        "Are you sure you want to delete existing files and re-download?",
                        default=False,
                    ):
                        Console(stderr=True).print("[yellow]Aborted.[/yellow]")
                        ctx.exit(0)

                    # Delete existing media files
                    Console().print(
                        f"[yellow]Deleting {len(existing_files)} existing files...[/yellow]"
                    )
                    for file_path in existing_files:
                        try:
                            file_path.unlink()
                            # Also delete corresponding .info.json if it exists
                            info_json = file_path.with_suffix(file_path.suffix + ".info.json")
                            if info_json.exists():
                                info_json.unlink()
                            logger.debug(f"Deleted: {file_path}")
                        except OSError as e:
                            logger.warning(f"Failed to delete {file_path}: {e}")
                    Console().print("[green]✓ Existing files deleted[/green]\n")

            # Enable ignore_database to bypass podcast-archiver's database check
            logger.info("Force download: enabling ignore_database")
            ctx.params["ignore_database"] = True

        # Set --write-info-json to True by default if not explicitly set by user
        # This enables the episode database feature to index metadata
        # The original podcast-archiver command has this parameter with default=False,
        # but we want to change the default to True in the wrapped version
        if "write_info_json" in ctx.params:
            param_source = ctx.get_parameter_source("write_info_json")
            logger.debug(f"write_info_json parameter source: {param_source}")
            if param_source in (ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP):
                # User didn't explicitly set it, so enable it by default
                logger.info("Setting write_info_json=True for episode database compatibility")
                ctx.params["write_info_json"] = True

        for k, v in ctx.params.items():
            logger.debug(f"Param {k} | {type(v)}: {v}")

        # ctx.invoke(podcast_archiver_command.main)
        ctx.forward(podcast_archiver_command)

    # Copy podcast-archiver params and prepend our custom --force-download option
    # Need to prepend so it shows up in help before the podcast-archiver options
    force_download_option = click.Option(
        ["--force-download"],
        is_flag=True,
        default=False,
        help=(
            "Force re-download of episodes even if they already exist on disk. "
            "WARNING: This will delete existing episode files before downloading. "
            "You will be prompted for confirmation."
        ),
    )
    archiver_wrapped.params = [force_download_option] + podcast_archiver_command.params.copy()
    logger.debug(f"Attached podcast-archiver command: {archiver_wrapped}")


# Register overcast commands
sync.add_command(overcast)

# Register retrieval aliases
overcast_meta = click.Group(
    "overcast", help="Retrieve episode metadata and information via overcast plugin"
)
overcast_meta.add_command(transcripts)
overcast_meta.add_command(chapters)
meta.add_command(overcast_meta)

# Register download commands
cli.add_command(download)

# Register episode database commands under download group
download.add_command(episode_db)

cli.add_command(sql_cli.sql)

# Note: _attach_podcast_archiver_passthroughs is now called lazily
# from within the cli() function after logging is configured

if __name__ == "__main__":
    cli()
