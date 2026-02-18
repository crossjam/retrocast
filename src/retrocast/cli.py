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
from retrocast.datastore import Datastore
from retrocast.download_commands import download
from retrocast.episode_db_commands import episode_db
from retrocast.logging_config import setup_logging
from retrocast.overcast import overcast
from retrocast.process_commands import transcription

from . import sql_cli

_podcast_archiver_attached = False


@click.group(cls=DefaultGroup, default="about", default_if_no_args=True)
@click.version_option()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging output.")
@click.option("-q", "--quiet", is_flag=True, help="Enable quiet mode (ERROR level logging only).")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Manage podcast subscriptions. Download episodes. Analyze with AI."""
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


@cli.group(name="configure")
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage the retrocast configuration data"""


@config.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Report configuration status without making changes"""
    from retrocast.datastore import Datastore

    console = Console()
    app_dir = get_app_dir(create=False)
    auth_path = get_auth_path(create=False)
    db_path = get_default_db_path(create=False)

    app_exists = app_dir.exists()
    auth_exists = auth_path.exists() if app_exists else False
    db_exists = db_path.exists() if app_exists else False
    db_initialized = Datastore.is_initialized(db_path) if app_exists else False

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
        "" if app_exists else "Run: retrocast configure initialize",
    )

    if app_exists:
        table.add_row(
            "Auth File",
            str(auth_path),
            "[green]✓ Found[/green]" if auth_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast subscribe overcast auth" if not auth_exists else "",
        )

        # Database row with initialization status
        if db_initialized:
            db_status = "[green]✓ Initialized[/green]"
            db_action = ""
        elif db_exists:
            db_status = "[yellow]⚠ Not initialized[/yellow]"
            db_action = "retrocast configure initialize"
        else:
            db_status = "[yellow]⚠ Missing[/yellow]"
            db_action = "retrocast configure initialize"

        table.add_row(
            "Database",
            str(db_path),
            db_status,
            db_action,
        )
    else:
        table.add_row("Auth File", str(auth_path), "[dim]n/a[/dim]", "Initialize app directory")
        table.add_row("Database", str(db_path), "[dim]n/a[/dim]", "Initialize app directory")

    console.print()
    console.print(table)
    console.print()

    if app_exists and auth_exists and db_initialized:
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

    # Initialize database schemas
    from retrocast.datastore import Datastore

    db_path = get_default_db_path(create=True)
    db = Datastore(db_path)  # noqa: F841 - Instantiation triggers schema initialization

    console.print()
    console.print("[bold cyan]retrocast Initialization[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")
    table.add_row("Config directory:", str(app_dir))
    table.add_row("Auth path:", str(get_auth_path(create=True)))
    table.add_row("Database path:", str(db_path))
    table.add_row("Database schemas:", "[green]✓ Initialized[/green]")

    console.print(table)
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Authenticate: [cyan]retrocast subscribe overcast auth[/cyan]")
    console.print("  2. Sync data:    [cyan]retrocast subscribe overcast save[/cyan]")
    console.print("  3. Download:     [cyan]retrocast subscribe overcast transcripts[/cyan]")
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
@click.option(
    "-d",
    "--db-path",
    "db_path_flag",
    is_flag=True,
    help="Output only the database path as a JSON string",
)
@click.option(
    "-a",
    "--app-dir",
    "app_dir_flag",
    is_flag=True,
    help="Output only the app directory path as a JSON string",
)
@click.pass_context
def location(ctx: click.Context, output_format, db_path_flag: bool, app_dir_flag: bool) -> None:
    """Output the location of the configuration directory.

    By default, displays a formatted table showing all configuration paths.
    Use --format json to output all paths as a JSON object.
    Use --db-path to output only the database path as a JSON string.
    Use --app-dir to output only the app directory path as a JSON string.

    Examples:
        retrocast configure location              # Table view
        retrocast configure location --format json  # All paths as JSON
        retrocast configure location --db-path    # Just database path
        retrocast configure location --app-dir    # Just app directory
    """

    # Validate mutual exclusivity of output options
    output_modes = [
        output_format != LocationOutput.CONSOLE,  # --format json specified
        db_path_flag,
        app_dir_flag,
    ]

    if sum(output_modes) > 1:
        raise click.UsageError(
            "Only one output option can be used at a time: --format, --db-path, or --app-dir"
        )

    console = Console()
    app_dir = get_app_dir(create=False)
    auth_path = get_auth_path(create=False)
    db_path = get_default_db_path(create=False)

    app_exists = app_dir.exists()
    auth_exists = auth_path.exists() if app_exists else False
    db_exists = db_path.exists() if app_exists else False

    # Handle --db-path flag
    if db_path_flag:
        json.dump(str(db_path), fp=sys.stdout)
        ctx.exit(0)

    # Handle --app-dir flag
    if app_dir_flag:
        json.dump(str(app_dir), fp=sys.stdout)
        ctx.exit(0)

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
        "" if app_exists else "Run: retrocast configure initialize",
    )

    if app_exists:
        table.add_row(
            "Auth File",
            str(auth_path),
            "[green]✓ Found[/green]" if auth_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast subscribe overcast auth" if not auth_exists else "",
        )
        table.add_row(
            "Database",
            str(db_path),
            "[green]✓ Found[/green]" if db_exists else "[yellow]⚠ Missing[/yellow]",
            "retrocast subscribe overcast save" if not db_exists else "",
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


@config.command(name="reset-db")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be reset without actually performing the reset.",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt and proceed with reset.",
)
@click.pass_context
def reset_db(ctx: click.Context, dry_run: bool, yes: bool) -> None:
    """Reset the database schema (WARNING: destroys all data)"""

    def format_truncated_list(items: list[str], max_items: int) -> str:
        """Format a list with truncation indicator if needed."""
        if len(items) <= max_items:
            return ", ".join(items)
        shown = ", ".join(items[:max_items])
        remaining = len(items) - max_items
        return f"{shown} ... (+{remaining} more)"

    console = Console()
    db_path = get_default_db_path(create=False)

    if not db_path.exists():
        console.print("[yellow]Database does not exist. Nothing to reset.[/yellow]")
        console.print(f"Database path: {db_path}")
        ctx.exit(0)

    # Open database connection to get schema info
    try:
        datastore = Datastore(db_path)
        schema_info = datastore.get_schema_info()
    except Exception as e:
        console.print(f"[red]Error accessing database: {e}[/red]")
        ctx.exit(1)

    # Display what will be reset
    console.print()
    console.print("[bold cyan]Database Schema Reset[/bold cyan]")
    console.print()
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print()

    if dry_run:
        console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]")
        console.print()

    # Create summary table
    table = Table(
        title="Schema Objects to Reset",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Object Type", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Names", style="dim")

    table.add_row(
        "Tables",
        str(len(schema_info["tables"])),
        format_truncated_list(schema_info["tables"], 5),
    )
    table.add_row(
        "Views",
        str(len(schema_info["views"])),
        ", ".join(schema_info["views"]),
    )
    table.add_row(
        "Indices",
        str(len(schema_info["indices"])),
        f"{len(schema_info['indices'])} indices will be recreated",
    )
    table.add_row(
        "FTS Tables",
        str(len(schema_info["fts_tables"])),
        format_truncated_list(schema_info["fts_tables"], 3),
    )
    table.add_row(
        "Triggers",
        str(len(schema_info["triggers"])),
        f"{len(schema_info['triggers'])} triggers will be recreated",
    )

    console.print(table)
    console.print()

    if dry_run:
        console.print("[bold]Actions that would be performed:[/bold]")
        console.print("  1. Drop all triggers")
        console.print("  2. Drop all views")
        console.print("  3. Drop all indices")
        console.print("  4. Drop all FTS tables")
        console.print("  5. Drop all tables")
        console.print("  6. Recreate schema from scratch")
        console.print()
        console.print("[green]✓ Dry run complete. No changes made.[/green]")
        ctx.exit(0)

    # Warn about data loss
    console.print(
        "[bold red]⚠ WARNING: This will permanently delete ALL data in the database![/bold red]"
    )
    console.print()

    # Confirm with user unless -y flag is provided
    if not yes:
        if not click.confirm(
            "Are you sure you want to reset the database schema?",
            default=False,
        ):
            console.print("[yellow]Reset cancelled.[/yellow]")
            ctx.exit(0)

    # Perform the reset
    console.print()
    console.print("[bold]Resetting database schema...[/bold]")

    try:
        datastore.reset_schema()
        console.print("[green]✓ Database schema reset successfully![/green]")
        console.print()
        console.print("[dim]The database has been reset to a clean state with empty tables.[/dim]")
        console.print("[dim]Run 'retrocast subscribe overcast save' to populate with data.[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Error resetting database: {e}[/red]")
        logger.exception("Database reset failed")
        ctx.exit(1)


@cli.group()
@click.pass_context
def subscribe(ctx: click.Context) -> None:
    """Manage feed subscriptions"""
    pass


@cli.group()
@click.pass_context
def index(ctx: click.Context) -> None:
    """Create and manage search indexes"""
    pass


@index.command()
def status() -> None:
    """Show index command availability"""
    Console().print("[yellow]Index management commands are not implemented yet.[/yellow]")


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
    def archiver_wrapped(ctx: rich_click.RichContext, **kwargs):
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

    archiver_wrapped.params = podcast_archiver_command.params.copy()
    logger.debug(f"Attached llm command: {archiver_wrapped}")


# Register subscription commands
subscribe.add_command(overcast)

# Register download commands
cli.add_command(download)

# Register episode database commands under download group
download.add_command(episode_db)

# Register transcription commands (transcribe, search, backends)
cli.add_command(transcription)

cli.add_command(sql_cli.sql)
cli.add_command(index)


@cli.command(name="chat")
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to retrocast database (defaults to app directory database)",
)
@click.option(
    "-m",
    "--model",
    "model_name",
    default="claude-sonnet-4-20250514",
    help="Anthropic model to use for the agent",
)
@click.option(
    "--rebuild-index",
    is_flag=True,
    help="Rebuild the ChromaDB index from scratch",
)
@click.pass_context
def castchat(
    ctx: click.Context,
    db_path: Path | None,
    model_name: str,
    rebuild_index: bool,
) -> None:
    """Interactive AI chat for exploring transcribed podcast content.

    Start an interactive REPL session powered by PydanticAI to explore your
    podcast transcription archive using natural language queries. The agent
    can search across all transcribed episodes to answer questions about
    topics, guests, and specific content.

    Requires chromadb and pydantic-ai dependencies:
        pip install retrocast[castchat]

    Example queries:
      - What episodes discussed machine learning?
      - Where did they talk about climate change?
      - Which episodes featured interviews with scientists?
    """
    try:
        from retrocast.castchat_agent import create_castchat_agent
        from retrocast.chromadb_manager import ChromaDBManager
    except ImportError as e:
        console = Console()
        console.print("[bold red]Error:[/bold red] castchat dependencies not installed")
        console.print("\nInstall with: [cyan]pip install retrocast[castchat][/cyan]")
        console.print(f"\nMissing: {e.name}")
        raise click.Abort()

    console = Console()

    # Get database path
    if db_path is None:
        db_path = get_default_db_path(create=False)

    if not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Database not found at {db_path}")
        console.print("Run [cyan]retrocast subscribe overcast[/cyan] first to create the database")
        raise click.Abort()

    # Initialize datastore
    from retrocast.datastore import Datastore

    datastore = Datastore(db_path)

    # Get app directory for ChromaDB storage
    app_dir = get_app_dir(create=True)
    chroma_dir = app_dir / "chromadb"

    # Initialize ChromaDB manager
    console.print(f"[dim]Initializing ChromaDB at {chroma_dir}...[/dim]")
    chroma_manager = ChromaDBManager(chroma_dir)

    # Check if index needs to be built or rebuilt
    current_count = chroma_manager.get_collection_count()

    if rebuild_index or current_count == 0:
        if rebuild_index:
            console.print("[yellow]Rebuilding index...[/yellow]")
            chroma_manager.reset()
        else:
            console.print("[yellow]Index is empty. Building initial index...[/yellow]")

        with console.status("[bold green]Indexing transcription segments..."):
            indexed_count = chroma_manager.index_transcriptions(datastore)

        if indexed_count == 0:
            console.print("[bold red]No transcription segments found![/bold red]")
            console.print(
                "Run [cyan]retrocast transcribe process[/cyan] to transcribe episodes first"
            )
            raise click.Abort()

        console.print(f"[green]✓[/green] Indexed {indexed_count:,} segments")
    else:
        console.print(f"[dim]Using existing index with {current_count:,} segments[/dim]")

    # Create agent
    console.print(f"[dim]Initializing agent with model: {model_name}...[/dim]")
    agent = create_castchat_agent(chroma_manager, model_name)

    # Launch clai REPL
    console.print("\n[bold green]Starting castchat REPL...[/bold green]")
    console.print("[dim]Type your questions or 'exit' to quit[/dim]\n")

    # Import clai and run
    try:
        # Run the REPL with our agent

        agent.to_cli_sync(prog_name="castchat")
    except ImportError:
        console.print(
            "[bold red]Error:[/bold red] clai command not found. "
            "Make sure pydantic-ai[cli] is installed."
        )
        raise click.Abort()
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")


# Note: _attach_podcast_archiver_passthroughs is now called lazily
# from within the cli() function after logging is configured

if __name__ == "__main__":
    cli()
