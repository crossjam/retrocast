"""CLI commands for managing search indexes."""

from pathlib import Path

import click
from click import Context
from loguru import logger
from rich.console import Console

from retrocast.appdir import get_app_dir, get_default_db_path
from retrocast.datastore import Datastore
from retrocast.index.manager import ChromaDBManager


@click.group()
@click.pass_context
def index(ctx: Context) -> None:
    """Create and manage search indexes."""
    logger.debug("Index command group invoked")


@index.group()
@click.pass_context
def vector(ctx: Context) -> None:
    """Manage vector search indexes."""
    logger.debug("Vector command group invoked")


@vector.command(name="build")
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Path to the retrocast SQLite database.",
)
@click.option(
    "--rebuild",
    is_flag=True,
    default=False,
    help="Force a full rebuild of the index, deleting existing data.",
)
@click.pass_context
def build_vector_index(ctx: Context, db_path: Path | None, rebuild: bool) -> None:
    """Build or update the vector search index from transcription data."""
    console = Console()

    # Determine database path
    if db_path is None:
        db_path = get_default_db_path(create=False)

    if not db_path or not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Database not found at '{db_path}'.")
        console.print("  - Use the --database option to specify the path.")
        console.print("  - Or run 'retrocast subscribe overcast' to create a default database.")
        raise click.Abort()

    # Initialize Datastore
    try:
        datastore = Datastore(db_path)
    except Exception as e:
        console.print(f"[bold red]Error connecting to database:[/bold red] {e}")
        raise click.Abort()

    # Get app directory for ChromaDB storage
    app_dir = get_app_dir(create=True)
    chroma_dir = app_dir / "chromadb"

    # Initialize ChromaDB manager
    console.print(f"[dim]Initializing vector index at: {chroma_dir}[/dim]")
    try:
        chroma_manager = ChromaDBManager(chroma_dir)
    except Exception as e:
        console.print(f"[bold red]Error initializing ChromaDB:[/bold red] {e}")
        console.print("  - Ensure 'retrocast[castchat]' dependencies are installed.")
        raise click.Abort()

    # Check if a rebuild is requested
    if rebuild:
        console.print("[yellow]Rebuilding index from scratch...[/yellow]")
        with console.status("[bold green]Resetting index..."):
            chroma_manager.reset()
        console.print("[green]✓[/green] Index reset complete.")

    # Perform indexing
    console.print("[cyan]Starting transcription indexing...[/cyan]")
    with console.status("[bold green]Processing transcription segments..."):
        try:
            indexed_count = chroma_manager.index_transcriptions(datastore)
        except Exception as e:
            console.print(f"[bold red]Failed to index transcriptions:[/bold red] {e}")
            logger.exception("Transcription indexing process failed.")
            raise click.Abort()

    if indexed_count > 0:
        total_segments = chroma_manager.get_collection_count()
        console.print(f"[green]✓[/green] Successfully indexed {indexed_count:,} new segments.")
        console.print(f"Total indexed segments: {total_segments:,}")
    else:
        console.print("[yellow]No new transcription segments found to index.[/yellow]")

    console.print("\n[bold green]Vector index is up to date.[/bold green]")
