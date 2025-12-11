"""CLI commands for managing the episode downloads database."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from retrocast.appdir import get_app_dir, get_default_db_path
from retrocast.datastore import Datastore
from retrocast.episode_scanner import EpisodeScanner
from retrocast.logging_config import get_logger

console = Console()
stderr_console = Console(stderr=True)


@click.group(name="db")
@click.pass_context
def episode_db(ctx: click.RichContext) -> None:
    """Manage downloaded episodes database."""
    ctx.ensure_object(dict)


@episode_db.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be created without making changes.",
)
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Path to database file. Defaults to app directory.",
)
@click.pass_context
def init(
    ctx: click.RichContext,
    dry_run: bool,
    db_path: Path | None,
) -> None:
    """Initialize episode downloads database schema.

    Creates the episode_downloads table and indexes in the retrocast database.
    This command is idempotent and safe to run multiple times.
    """
    ctx.ensure_object(dict)
    logger = get_logger("retrocast.download.db.init")

    # Get database path
    if db_path is None:
        db_path = get_default_db_path(create=True)

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
        console.print(f"Would initialize database at: [blue]{db_path}[/blue]")
        console.print("\nWould create:")
        console.print("  • episode_downloads table")
        console.print("  • episode_downloads_fts (full-text search)")
        console.print("  • Indexes on podcast_title, publication_date, modified_time")
        console.print("  • FTS triggers for automatic sync")
        return

    # Initialize datastore
    logger.info(f"Initializing database at {db_path}")
    datastore = Datastore(db_path)

    # Ensure episode_downloads table exists
    datastore.ensure_episode_downloads_table()

    console.print(f"[green]✓[/green] Database initialized at [blue]{db_path}[/blue]")
    console.print("[green]✓[/green] episode_downloads table created")
    console.print("[green]✓[/green] Full-text search enabled")
    console.print("[green]✓[/green] Indexes created")

    logger.info("Database initialization complete")


@episode_db.command()
@click.option(
    "--rescan",
    is_flag=True,
    help="Delete existing records and rebuild from scratch.",
)
@click.option(
    "--verify",
    is_flag=True,
    help="Verify all files still exist and mark missing ones.",
)
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Path to database file. Defaults to app directory.",
)
@click.option(
    "--downloads-dir",
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Path to episode_downloads directory. Defaults to app directory.",
)
@click.pass_context
def update(
    ctx: click.RichContext,
    rescan: bool,
    verify: bool,
    db_path: Path | None,
    downloads_dir: Path | None,
) -> None:
    """Update episode downloads database from filesystem.

    Scans the episode_downloads directory and updates the database with
    discovered episodes and their metadata from .info.json files.
    """
    ctx.ensure_object(dict)
    logger = get_logger("retrocast.download.db.update")

    # Get paths
    app_dir = get_app_dir(create=True)
    if db_path is None:
        db_path = get_default_db_path(create=True)
    if downloads_dir is None:
        downloads_dir = app_dir / "episode_downloads"

    # Check if downloads directory exists
    if not downloads_dir.exists():
        stderr_console.print(
            f"[red]Downloads directory does not exist:[/red] [blue]{downloads_dir}[/blue]",
        )
        stderr_console.print(
            "\n[yellow]Hint:[/yellow] Download some episodes first using:",
        )
        stderr_console.print("  retrocast download podcast-archiver <feed_url>")
        ctx.exit(1)

    # Initialize datastore and scanner
    logger.info(f"Updating database at {db_path}")
    datastore = Datastore(db_path)
    datastore.ensure_episode_downloads_table()
    scanner = EpisodeScanner(downloads_dir)

    # Rescan mode: clear existing data
    if rescan:
        logger.info("Rescan mode: clearing existing episode_downloads records")
        console.print("[yellow]Clearing existing records...[/yellow]")
        datastore.db.execute("DELETE FROM episode_downloads")
        console.print("[green]✓[/green] Existing records cleared")

    # Scan filesystem
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning episode_downloads directory...", total=None)
        episodes = scanner.scan()
        progress.update(task, completed=True)

    if not episodes:
        console.print(
            "[yellow]No episodes found in[/yellow] [blue]{downloads_dir}[/blue]",
        )
        console.print(
            "\n[yellow]Hint:[/yellow] Download some episodes first using:",
        )
        console.print("  retrocast download podcast-archiver <feed_url>")
        return

    console.print(f"[green]Found {len(episodes)} episode(s)[/green]")

    # Process episodes and build records
    records = []
    existing_paths = set()
    now = datetime.now().isoformat()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing episode metadata...", total=len(episodes))

        for episode_info in episodes:
            existing_paths.add(str(episode_info.media_path))

            # Build base record
            record = {
                "media_path": str(episode_info.media_path),
                "podcast_title": episode_info.podcast_title,
                "episode_filename": episode_info.episode_filename,
                "file_size": episode_info.file_size,
                "modified_time": episode_info.modified_time.isoformat(),
                "discovered_time": now,
                "last_verified_time": now,
                "metadata_exists": 1 if episode_info.metadata_exists else 0,
                "media_exists": 1,
            }

            # Extract metadata if available
            if episode_info.metadata_exists and episode_info.metadata_path:
                metadata = scanner.read_metadata(episode_info.metadata_path)
                if metadata:
                    # Store full JSON
                    record["metadata_json"] = json.dumps(metadata)

                    # Extract and add fields
                    extracted = scanner.extract_fields(metadata)
                    record.update(extracted)

            records.append(record)
            progress.update(task, advance=1)

    # Batch upsert to database
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Updating database...", total=None)
        datastore.upsert_episode_downloads_batch(records)
        progress.update(task, completed=True)

    # Mark missing episodes if verify mode
    missing_count = 0
    if verify:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Verifying existing records...", total=None)
            missing_count = datastore.mark_missing_episodes(existing_paths)
            progress.update(task, completed=True)

    # Display summary
    table = Table(title="Update Summary", show_lines=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Episodes found", str(len(episodes)))
    table.add_row("With metadata", str(sum(1 for e in episodes if e.metadata_exists)))
    table.add_row(
        "Without metadata",
        str(sum(1 for e in episodes if not e.metadata_exists)),
    )
    if verify:
        table.add_row("Missing files", str(missing_count))

    console.print(table)
    console.print(f"[green]✓[/green] Database updated at [blue]{db_path}[/blue]")

    logger.info(f"Update complete: {len(episodes)} episodes processed")


@episode_db.command()
@click.argument("query")
@click.option(
    "--podcast",
    help="Filter by podcast title (exact match).",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Maximum number of results to display.",
)
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Path to database file. Defaults to app directory.",
)
@click.pass_context
def search(
    ctx: click.RichContext,
    query: str,
    podcast: str | None,
    limit: int,
    db_path: Path | None,
) -> None:
    """Search episode downloads using full-text search.

    Searches episode titles, descriptions, summaries, and shownotes.

    Examples:
        retrocast download db search "python"
        retrocast download db search "machine learning" --podcast "Practical AI"
        retrocast download db search "interview" --limit 10
    """
    ctx.ensure_object(dict)
    logger = get_logger("retrocast.download.db.search")

    # Get database path
    if db_path is None:
        db_path = get_default_db_path()

    if not db_path.exists():
        stderr_console.print(
            f"[red]Database not found:[/red] [blue]{db_path}[/blue]",
        )
        stderr_console.print(
            "\n[yellow]Hint:[/yellow] Initialize the database first:",
        )
        stderr_console.print("  retrocast download db init")
        stderr_console.print("  retrocast download db update")
        ctx.exit(1)

    # Initialize datastore
    datastore = Datastore(db_path)

    # Perform search
    logger.info(f"Searching for: {query}")
    results = datastore.search_episode_downloads(query)

    # Filter by podcast if specified
    if podcast:
        results = [r for r in results if r.get("podcast_title") == podcast]

    # Apply limit
    results = results[:limit]

    if not results:
        console.print(f"[yellow]No results found for:[/yellow] {query}")
        if podcast:
            console.print(f"[yellow]in podcast:[/yellow] {podcast}")
        return

    # Display results in table
    table = Table(
        title=f"Search Results: '{query}'" + (f" in '{podcast}'" if podcast else ""),
        show_lines=True,
    )
    table.add_column("Podcast", style="cyan", no_wrap=True)
    table.add_column("Episode", style="green")
    table.add_column("Date", style="blue")
    table.add_column("Duration", justify="right")

    for result in results:
        episode_title = result.get("episode_title") or result.get("episode_filename")
        podcast_title = result.get("podcast_title") or "Unknown"
        pub_date = result.get("publication_date") or ""
        if pub_date:
            # Format date nicely
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                pub_date = dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                pass

        duration = result.get("duration")
        duration_str = ""
        if duration:
            # Format duration as HH:MM:SS
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"

        # Truncate long titles
        if len(episode_title) > 60:
            episode_title = episode_title[:57] + "..."
        if len(podcast_title) > 30:
            podcast_title = podcast_title[:27] + "..."

        table.add_row(podcast_title, episode_title, pub_date, duration_str)

    console.print(table)
    console.print(
        f"\n[green]Found {len(results)} result(s)[/green]"
        + (f" [dim](limited to {limit})[/dim]" if len(results) == limit else ""),
    )

    logger.info(f"Search complete: {len(results)} results found")


__all__ = ["episode_db"]
