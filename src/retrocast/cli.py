#!/usr/bin/env python

import click
from click_default_group import DefaultGroup
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from retrocast.about_content import load_about_markdown
from retrocast.appdir import get_app_dir
from retrocast.crawl_commands import crawl
from retrocast.logging_config import setup_logging
from retrocast.overcast import overcast


@click.group(cls=DefaultGroup, default="about", default_if_no_args=True)
@click.version_option()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Save listening history and feed/episode info from Overcast to SQLite."""
    # Initialize context object if it doesn't exist
    ctx.ensure_object(dict)
    # Store app directory in context
    ctx.obj["app_dir"] = get_app_dir()
    log_file = ctx.obj["app_dir"] / "retrocast.log"
    ctx.obj["log_file"] = log_file
    ctx.obj["verbose"] = verbose
    setup_logging(verbose=verbose, log_file=log_file)


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


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize retrocast configuration directory."""
    console = Console()
    app_dir = get_app_dir()

    # Check if directory already exists
    already_exists = app_dir.exists()

    # Ensure the directory exists
    if not already_exists:
        app_dir.mkdir(parents=True, exist_ok=True)

    console.print()
    console.print("[bold cyan]Retrocast Initialization[/bold cyan]")
    console.print()

    # Create status table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")

    table.add_row("Config directory:", str(app_dir))

    if already_exists:
        table.add_row("Status:", "[yellow]✓ Already exists[/yellow]")
    else:
        table.add_row("Status:", "[green]✓ Created[/green]")

    console.print(table)
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Authenticate: [cyan]retrocast sync overcast auth[/cyan]")
    console.print("  2. Sync data:    [cyan]retrocast sync overcast save[/cyan]")
    console.print("  3. Check status: [cyan]retrocast sync overcast check[/cyan]")
    console.print()


@cli.group()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Synchronization commands."""
    pass


# Register overcast commands
sync.add_command(overcast)

# Register crawl commands
cli.add_command(crawl)


if __name__ == "__main__":
    cli()
