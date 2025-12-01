#!/usr/bin/env python

import sys
import tarfile
from contextlib import nullcontext
from pathlib import Path

import click
from click_default_group import DefaultGroup
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from retrocast.about_content import load_about_markdown
from retrocast.appdir import ensure_app_dir, get_app_dir, get_auth_path, get_default_db_path
from retrocast.crawl_commands import crawl
from retrocast.logging_config import setup_logging
from retrocast.overcast import chapters, overcast, transcripts


@click.group(cls=DefaultGroup, default="about", default_if_no_args=True)
@click.version_option()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Save listening history and feed/episode info from Overcast to SQLite."""
    # Initialize context object if it doesn't exist
    ctx.ensure_object(dict)
    # Store app directory in context
    app_dir = get_app_dir(create=False)
    ctx.obj["app_dir"] = app_dir
    log_file = app_dir / "retrocast.log"
    ctx.obj["log_file"] = log_file
    ctx.obj["verbose"] = verbose
    setup_logging(app_dir, verbose=verbose, log_file=log_file, enable_file_logging=app_dir.exists())


@cli.command()
def about() -> None:
    """Show information about Retrocast."""
    console = Console()

    try:
        about_text = load_about_markdown()
    except (FileNotFoundError, OSError):
        console.print("[bold red]Unable to load Retrocast about information.[/bold red]")
        return

    console.print(Markdown(about_text))


@cli.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage the Retrocast configuration directory."""


@config.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Report configuration status without making changes."""

    console = Console()
    app_dir = get_app_dir(create=False)
    auth_path = get_auth_path(create=False)
    db_path = get_default_db_path(create=False)

    app_exists = app_dir.exists()
    auth_exists = auth_path.exists() if app_exists else False
    db_exists = db_path.exists() if app_exists else False

    table = Table(
        title="Retrocast Configuration",
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
    """Create the Retrocast configuration directory."""

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
        log_file=ctx.obj.get("log_file"),
        enable_file_logging=True,
    )

    console.print()
    console.print("[bold cyan]Retrocast Initialization[/bold cyan]")
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
    console.print("  3. Download:     [cyan]retrocast retrieve overcast transcripts[/cyan]")
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
    """Archive the configuration directory as a gzipped tarball."""

    console = Console(stderr=True)
    app_dir = get_app_dir(create=False)

    if not app_dir.exists():
        console.print("[red]Configuration directory not found. Initialize it first.[/red]")
        ctx.exit(1)

    stream = sys.stdout.buffer
    stream_context = nullcontext(stream)

    if output_path is not None:
        if output_path.exists() and not force:
            if not click.confirm(
                f"Overwrite existing archive at {output_path}?",
                default=False,
            ):
                console.print("[yellow]Archive cancelled.[/yellow]")
                ctx.exit(1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stream_context = output_path.open("wb")

    with stream_context as file_obj:
        with tarfile.open(
            fileobj=file_obj,
            mode="w:gz",
            compresslevel=compression_level,
        ) as tar:
            tar.add(app_dir, arcname=app_dir.name)

    if output_path is not None:
        console.print(f"[green]Archive written to {output_path}[/green]")


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Deprecated: initialize configuration (use `config initialize`)."""

    console = Console()
    console.print(
        "[yellow]`retrocast init` is deprecated. Using "
        "`retrocast config initialize` instead.[/yellow]",
    )
    ctx.invoke(config_initialize, yes=False)


@cli.group()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Metadata synchronization commands."""
    pass


@cli.group()
@click.pass_context
def retrieve(ctx: click.Context) -> None:
    """Media download commands."""
    pass


# Register overcast commands
sync.add_command(overcast)

# Register retrieval aliases
overcast_retrieve = click.Group("overcast", help="Overcast media retrieval commands.")
overcast_retrieve.add_command(transcripts)
overcast_retrieve.add_command(chapters)
retrieve.add_command(overcast_retrieve)

# Register crawl commands
cli.add_command(crawl)


if __name__ == "__main__":
    cli()
