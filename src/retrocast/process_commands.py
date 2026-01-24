"""CLI commands for processing podcast audio files (transcription, analysis)."""

from pathlib import Path
from typing import Optional

import rich_click as click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from retrocast.appdir import get_app_dir, get_default_db_path
from retrocast.datastore import Datastore
from retrocast.transcription import TranscriptionManager

console = Console()

# Supported audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac", ".aac"}


@click.group(name="transcription")
@click.pass_context
def transcription(ctx: click.RichContext) -> None:
    """Manage audio transcriptions (create, search, analyze)."""
    ctx.ensure_object(dict)


@transcription.command(name="process")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
    required=False,
)
@click.option(
    "--from-downloads",
    is_flag=True,
    help="Process episodes from the episode_downloads directory.",
)
@click.option(
    "--podcast",
    "podcast_filter",
    type=str,
    default=None,
    help="Filter by podcast name (use with --from-downloads or directory paths).",
)
@click.option(
    "--list-podcasts",
    is_flag=True,
    help="List available podcasts from downloads and exit.",
)
@click.option(
    "--backend",
    type=click.Choice(["auto", "mlx-whisper", "faster-whisper"], case_sensitive=False),
    default="auto",
    help="Transcription backend to use.",
)
@click.option(
    "--model",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    default="base",
    help="Whisper model size.",
)
@click.option(
    "--language",
    type=str,
    default=None,
    help="Audio language code (e.g., 'en', 'es'). Auto-detected if not specified.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for transcription files (defaults to app_dir/transcriptions).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["txt", "json", "srt", "vtt"]),
    default="json",
    help="Output format for transcription files.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-transcribe even if transcription already exists.",
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def process_audio(  # noqa: C901
    ctx: click.RichContext,
    paths: tuple[Path, ...],
    from_downloads: bool,
    podcast_filter: Optional[str],
    list_podcasts: bool,
    backend: str,
    model: str,
    language: Optional[str],
    output_dir: Optional[Path],
    output_format: str,
    force: bool,
    db_path: Optional[Path],
) -> None:
    """Process audio files to create transcriptions.

    PATHS: One or more audio files or directories containing audio files.
    Can be omitted when using --from-downloads.

    Examples:

        # Process a single file
        retrocast transcription process episode.mp3

        # Process all files in a directory
        retrocast transcription process /path/to/podcast/

        # Use specific backend and model
        retrocast transcription process --backend mlx-whisper --model medium file.mp3

        # Save as SRT subtitle format
        retrocast transcription process --format srt episode.mp3

        # Process all downloaded episodes from a specific podcast
        retrocast transcription process --from-downloads --podcast "Tech Podcast"

        # List available podcasts from downloads
        retrocast transcription process --list-podcasts

        # Process all downloaded episodes
        retrocast transcription process --from-downloads
    """
    # Setup
    app_dir = get_app_dir(create=True)
    if output_dir is None:
        output_dir = app_dir / "transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    if db_path is None:
        db_path = get_default_db_path(create=True)

    # Initialize datastore
    datastore = Datastore(db_path)

    # Handle --list-podcasts
    if list_podcasts:
        _list_downloaded_podcasts(datastore, app_dir)
        return

    # Collect audio files
    audio_files: list[Path] = []
    podcast_metadata: dict[Path, str] = {}  # Map file path to podcast title

    if from_downloads:
        # Get files from episode_downloads directory
        downloads_dir = app_dir / "episode_downloads"

        if not downloads_dir.exists():
            console.print(
                f"[red]Episode downloads directory not found: {downloads_dir}[/red]\n"
                "Use 'retrocast download podcast-archiver' to download episodes first."
            )
            ctx.exit(1)

        # Get episodes from database if available, otherwise scan filesystem
        downloaded_podcasts = datastore.get_downloaded_podcasts()

        if downloaded_podcasts:
            # Use database to get episode list
            if podcast_filter:
                # Check if podcast exists
                matching = [
                    p
                    for p in downloaded_podcasts
                    if podcast_filter.lower() in p["podcast_title"].lower()
                ]
                if not matching:
                    console.print(f"[red]No podcast found matching: {podcast_filter}[/red]\n")
                    _list_downloaded_podcasts(datastore, app_dir)
                    ctx.exit(1)

                # If multiple matches, show them
                if len(matching) > 1:
                    exact_match = [
                        p for p in matching if p["podcast_title"].lower() == podcast_filter.lower()
                    ]
                    if exact_match:
                        matching = exact_match
                    else:
                        console.print(
                            f"[yellow]Multiple podcasts match '{podcast_filter}':[/yellow]"
                        )
                        for p in matching:
                            title = p["podcast_title"]
                            count = p["episode_count"]
                            console.print(f"  • {title} ({count} episodes)")
                        console.print("\n[dim]Please use a more specific name.[/dim]")
                        ctx.exit(1)

                podcast_name = matching[0]["podcast_title"]
                episodes = datastore.get_episode_downloads(podcast_title=podcast_name)
            else:
                episodes = datastore.get_episode_downloads()

            for ep in episodes:
                media_path = Path(ep["media_path"])
                if media_path.exists() and media_path.suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(media_path)
                    podcast_metadata[media_path] = ep.get("podcast_title", media_path.parent.name)

        else:
            # Fallback: scan filesystem directly
            console.print(
                "[dim]Note: Episode database not populated. "
                "Run 'retrocast download db update' for better podcast filtering.[/dim]\n"
            )
            for podcast_dir in downloads_dir.iterdir():
                if not podcast_dir.is_dir():
                    continue

                podcast_name = podcast_dir.name

                # Apply podcast filter if specified
                if podcast_filter:
                    if podcast_filter.lower() not in podcast_name.lower():
                        continue

                for media_file in podcast_dir.iterdir():
                    if media_file.is_file() and media_file.suffix.lower() in AUDIO_EXTENSIONS:
                        audio_files.append(media_file)
                        podcast_metadata[media_file] = podcast_name

    else:
        # Use provided paths
        if not paths:
            console.print(
                "[red]No paths specified.[/red]\n"
                "Provide audio files/directories or use --from-downloads.\n"
                "Use --help for more options."
            )
            ctx.exit(1)

        for path in paths:
            if path.is_file():
                if path.suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(path)
                    # Try to infer podcast name from parent directory
                    podcast_metadata[path] = path.parent.name
                else:
                    console.print(
                        f"[yellow]Skipping {path.name}: not a supported audio file[/yellow]"
                    )
            elif path.is_dir():
                # Apply podcast filter if the directory matches
                if podcast_filter:
                    if podcast_filter.lower() in path.name.lower():
                        # Process this directory
                        for ext in AUDIO_EXTENSIONS:
                            for f in path.rglob(f"*{ext}"):
                                audio_files.append(f)
                                podcast_metadata[f] = f.parent.name
                    else:
                        # Check subdirectories for matching podcast names
                        for subdir in path.iterdir():
                            if subdir.is_dir() and podcast_filter.lower() in subdir.name.lower():
                                for ext in AUDIO_EXTENSIONS:
                                    for f in subdir.rglob(f"*{ext}"):
                                        audio_files.append(f)
                                        podcast_metadata[f] = f.parent.name
                else:
                    # Find all audio files in directory
                    for ext in AUDIO_EXTENSIONS:
                        for f in path.rglob(f"*{ext}"):
                            audio_files.append(f)
                            podcast_metadata[f] = f.parent.name
            else:
                console.print(f"[yellow]Skipping {path}: not a file or directory[/yellow]")

    if not audio_files:
        if podcast_filter:
            console.print(f"[red]No audio files found for podcast: {podcast_filter}[/red]")
        else:
            console.print("[red]No audio files found to transcribe.[/red]")
        ctx.exit(1)

    # Show what we found
    if podcast_filter or from_downloads:
        unique_podcasts = set(podcast_metadata.values())
        if len(unique_podcasts) == 1:
            console.print(
                f"\n[bold]Found {len(audio_files)} episode(s) from "
                f"'{list(unique_podcasts)[0]}'[/bold]\n"
            )
        else:
            console.print(
                f"\n[bold]Found {len(audio_files)} episode(s) from "
                f"{len(unique_podcasts)} podcast(s)[/bold]\n"
            )
    else:
        console.print(f"\n[bold]Found {len(audio_files)} audio file(s) to transcribe[/bold]\n")

    # Initialize transcription manager
    try:
        manager = TranscriptionManager(
            backend=backend,
            model_size=model,
            output_dir=output_dir,
            datastore=datastore,
        )
    except RuntimeError as e:
        console.print(f"[red]Error initializing transcription: {e}[/red]")
        ctx.exit(1)

    # Temporarily disable loguru during transcription to clean up progress output
    from loguru import logger

    logger.disable("retrocast")

    try:
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            main_task = progress.add_task(
                "[cyan]Transcribing audio files...", total=len(audio_files)
            )

            success_count = 0
            skip_count = 0
            error_count = 0

            for audio_file in audio_files:
                # Update progress
                progress.update(
                    main_task,
                    description=f"[cyan]Transcribing {audio_file.name}...",
                )

                try:
                    # Transcribe - use metadata if available
                    podcast_title = podcast_metadata.get(audio_file, audio_file.parent.name)
                    result = manager.transcribe_file(
                        audio_path=audio_file,
                        podcast_title=podcast_title,
                        episode_title=audio_file.stem,
                        language=language,
                        output_format=output_format,
                        force=force,
                    )

                    console.print(
                        f"[green]✓[/green] {audio_file.name}: "
                        f"{result.word_count()} words, "
                        f"{result.duration:.1f}s, "
                        f"language: {result.language}"
                    )
                    success_count += 1

                except RuntimeError as e:
                    if "already exists" in str(e):
                        console.print(
                            f"[yellow]⊘[/yellow] {audio_file.name}: "
                            f"Already transcribed (use --force to re-transcribe)"
                        )
                        skip_count += 1
                    else:
                        console.print(f"[red]✗[/red] {audio_file.name}: {e}")
                        error_count += 1

                except Exception as e:
                    console.print(f"[red]✗[/red] {audio_file.name}: {e}")
                    error_count += 1

                # Update progress
                progress.update(main_task, advance=1)

        # Summary
        console.print(
            f"\n[bold]Transcription complete:[/bold] "
            f"[green]{success_count} succeeded[/green], "
            f"[yellow]{skip_count} skipped[/yellow], "
            f"[red]{error_count} failed[/red]\n"
        )
    finally:
        # Restore normal logging
        logger.enable("retrocast")


def _list_downloaded_podcasts(datastore: Datastore, app_dir: Path) -> None:
    """List available podcasts from the episode_downloads database.

    Args:
        datastore: Datastore instance
        app_dir: Application directory path
    """
    podcasts = datastore.get_downloaded_podcasts()

    if not podcasts:
        downloads_dir = app_dir / "episode_downloads"
        if not downloads_dir.exists():
            console.print(
                "\n[yellow]No downloaded episodes found.[/yellow]\n"
                "Use 'retrocast download podcast-archiver <feed_url>' to download episodes.\n"
            )
        else:
            # Try scanning filesystem
            console.print(
                "\n[yellow]Episode database not populated.[/yellow]\n"
                "Run 'retrocast download db update' to index downloaded episodes.\n"
            )
            # Show directories as fallback
            podcast_dirs = [
                d.name for d in downloads_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]
            if podcast_dirs:
                console.print("[dim]Available podcast directories:[/dim]")
                for name in sorted(podcast_dirs):
                    console.print(f"  • {name}")
                console.print()
        return

    console.print("\n[bold cyan]═══ Available Podcasts ═══[/bold cyan]\n")

    table = Table(show_header=True)
    table.add_column("Podcast", style="cyan", max_width=50)
    table.add_column("Episodes", justify="right")

    total_episodes = 0
    for podcast in podcasts:
        table.add_row(podcast["podcast_title"], str(podcast["episode_count"]))
        total_episodes += podcast["episode_count"]

    console.print(table)
    console.print(f"\n[dim]Total: {len(podcasts)} podcast(s), {total_episodes} episode(s)[/dim]")
    console.print(
        "\n[dim]Use --podcast <name> to select a specific podcast for transcription.[/dim]\n"
    )


@transcription.command(name="validate")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory containing transcription JSON files (defaults to app_dir/transcriptions).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation errors for each file.",
)
@click.pass_context
def validate_transcriptions(
    ctx: click.RichContext,
    output_dir: Optional[Path],
    verbose: bool,
) -> None:
    """Validate all JSON transcription files in the app directory.

    Checks that all JSON transcription files conform to the expected schema
    using pydantic validation. Displays progress during validation and provides
    a summary report at the end.

    Example:
        retrocast transcription validate
        retrocast transcription validate --verbose
        retrocast transcription validate --output-dir /custom/path
    """
    import json

    from pydantic import ValidationError

    from retrocast.transcription.models import TranscriptionJSONModel

    # Setup
    app_dir = get_app_dir(create=False)
    if output_dir is None:
        output_dir = app_dir / "transcriptions"

    if not output_dir.exists():
        console.print(
            f"[red]Transcription directory not found: {output_dir}[/red]\n"
            "No transcriptions to validate."
        )
        ctx.exit(1)

    # Find all JSON files
    json_files = list(output_dir.rglob("*.json"))

    if not json_files:
        console.print(
            f"[yellow]No JSON files found in {output_dir}[/yellow]\nNo transcriptions to validate."
        )
        ctx.exit(0)

    console.print(
        f"\n[bold cyan]Validating {len(json_files)} transcription file(s)...[/bold cyan]\n"
    )

    # Track results
    valid_files: list[Path] = []
    invalid_files: list[tuple[Path, str]] = []
    error_files: list[tuple[Path, str]] = []

    # Validate files with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Validating files...", total=len(json_files))

        for json_file in json_files:
            relative_path = json_file.relative_to(output_dir)
            progress.update(task, description=f"[cyan]Validating {relative_path}...")

            try:
                # Read JSON file
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Validate with pydantic
                TranscriptionJSONModel(**data)

                # Success
                valid_files.append(json_file)
                if verbose:
                    console.print(f"[green]✓[/green] {relative_path}")

            except json.JSONDecodeError as e:
                # JSON parsing error
                error_msg = f"JSON parse error: {str(e)}"
                error_files.append((json_file, error_msg))
                if verbose:
                    console.print(f"[red]✗[/red] {relative_path}: {error_msg}")

            except ValidationError as e:
                # Pydantic validation error
                error_msg = str(e)
                invalid_files.append((json_file, error_msg))
                if verbose:
                    console.print(f"[red]✗[/red] {relative_path}: Validation failed")
                    # Show first error only for brevity
                    errors = e.errors()
                    if errors:
                        first_error = errors[0]
                        console.print(
                            f"    [dim]Field: {first_error['loc']}, "
                                f"Error: {first_error['msg']}[/dim]"
                            )

            except Exception as e:
                # Other errors
                error_msg = f"Unexpected error: {str(e)}"
                error_files.append((json_file, error_msg))
                if verbose:
                    console.print(f"[red]✗[/red] {relative_path}: {error_msg}")

            progress.update(task, advance=1)

    # Display summary
    console.print("\n[bold cyan]═══ Validation Summary ═══[/bold cyan]\n")

    summary_table = Table(show_header=True, show_edge=False)
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Count", justify="right")
    summary_table.add_column("Percentage", justify="right")

    total = len(json_files)
    valid_pct = (len(valid_files) / total * 100) if total > 0 else 0
    invalid_pct = (len(invalid_files) / total * 100) if total > 0 else 0
    error_pct = (len(error_files) / total * 100) if total > 0 else 0

    summary_table.add_row(
        "[green]Valid[/green]",
        str(len(valid_files)),
        f"[green]{valid_pct:.1f}%[/green]",
    )
    summary_table.add_row(
        "[yellow]Invalid Schema[/yellow]",
        str(len(invalid_files)),
        f"[yellow]{invalid_pct:.1f}%[/yellow]",
    )
    summary_table.add_row(
        "[red]Parse Errors[/red]",
        str(len(error_files)),
        f"[red]{error_pct:.1f}%[/red]",
    )
    summary_table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total}[/bold]",
        "[bold]100.0%[/bold]",
    )

    console.print(summary_table)
    console.print()

    # Show details for invalid files if not in verbose mode
    if not verbose and (invalid_files or error_files):
        console.print("[dim]Run with --verbose to see detailed error messages.[/dim]\n")

    # Show invalid files details
    if invalid_files and not verbose:
        console.print(f"[yellow]Files with validation errors ({len(invalid_files)}):[/yellow]")
        for json_file, _ in invalid_files[:5]:  # Show first 5
            relative_path = json_file.relative_to(output_dir)
            console.print(f"  • {relative_path}")
        if len(invalid_files) > 5:
            console.print(f"  [dim]... and {len(invalid_files) - 5} more[/dim]")
        console.print()

    # Show error files details
    if error_files and not verbose:
        console.print(f"[red]Files with parse/read errors ({len(error_files)}):[/red]")
        for json_file, _ in error_files[:5]:  # Show first 5
            relative_path = json_file.relative_to(output_dir)
            console.print(f"  • {relative_path}")
        if len(error_files) > 5:
            console.print(f"  [dim]... and {len(error_files) - 5} more[/dim]")
        console.print()

    # Exit with appropriate status
    if invalid_files or error_files:
        ctx.exit(1)
    else:
        console.print("[bold green]✓ All transcription files are valid![/bold green]\n")
        ctx.exit(0)


@transcription.group(name="backends")
def backends() -> None:
    """Manage transcription backends.

    Commands for listing, testing, and managing transcription backends.
    """
    pass


@backends.command(name="list")
def list_backends() -> None:
    """List available transcription backends.

    Shows which backends are installed and available on your system.

    Example:
        retrocast transcription backends list
    """
    from retrocast.transcription.backends import get_all_backends

    table = Table(title="Available Transcription Backends", show_header=True)
    table.add_column("Backend", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Platform", style="dim")
    table.add_column("Description")

    backends = get_all_backends()

    if not backends:
        console.print("[yellow]No transcription backends found.[/yellow]")
        console.print(
            "\nInstall a backend:\n"
            "  • macOS (Apple Silicon): pip install mlx-whisper\n"
            "  • Linux/CUDA: pip install faster-whisper torch\n"
            "  • CPU-only: pip install faster-whisper torch\n"
        )
        return

    for backend_cls in backends:
        backend = backend_cls()
        is_available = backend.is_available()

        status = "[green]✓ Available[/green]" if is_available else "[red]✗ Not Available[/red]"

        table.add_row(
            backend.name,
            status,
            backend.platform_info(),
            backend.description(),
        )

    console.print(table)

    # Show installation hints
    unavailable = [b() for b in backends if not b().is_available()]
    if unavailable:
        console.print("\n[dim]To install unavailable backends:[/dim]")
        for backend in unavailable:
            if backend.name == "mlx-whisper":
                console.print("  • mlx-whisper: pip install mlx-whisper")
            elif backend.name == "faster-whisper":
                console.print("  • faster-whisper: pip install faster-whisper torch")


@backends.command(name="test")
@click.argument("backend_name", type=str)
def test_backend(backend_name: str) -> None:
    """Test if a specific backend is available.

    BACKEND_NAME: Name of backend to test (e.g., 'mlx-whisper')

    Example:
        retrocast transcription backends test mlx-whisper
    """
    from retrocast.transcription.backends import get_all_backends

    backends = get_all_backends()
    backend_names = {b().name: b for b in backends}

    if backend_name not in backend_names:
        console.print(f"[red]Unknown backend: {backend_name}[/red]")
        console.print(f"\nAvailable backends: {', '.join(backend_names.keys())}")
        return

    backend_cls = backend_names[backend_name]
    backend = backend_cls()

    console.print(f"\n[bold]Testing backend: {backend.name}[/bold]\n")
    console.print(f"  Platform: {backend.platform_info()}")
    console.print(f"  Description: {backend.description()}")

    is_available = backend.is_available()

    if is_available:
        console.print(
            f"\n[green]✓ Backend '{backend.name}' is available and ready to use![/green]\n"
        )
    else:
        console.print(f"\n[red]✗ Backend '{backend.name}' is not available.[/red]")
        console.print("\n[yellow]Possible reasons:[/yellow]")
        console.print("  • Required dependencies not installed")
        console.print("  • Platform not supported")
        console.print(f"\n[dim]Try installing: pip install {backend.name}[/dim]\n")


@transcription.command()
@click.argument("query", type=str, required=True)
@click.option(
    "--podcast",
    type=str,
    default=None,
    help="Filter by podcast title.",
)
@click.option(
    "--speaker",
    type=str,
    default=None,
    help="Filter by speaker ID (requires diarization).",
)
@click.option(
    "--backend",
    type=str,
    default=None,
    help="Filter by transcription backend (e.g., 'mlx-whisper').",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Filter by model size (e.g., 'base', 'medium').",
)
@click.option(
    "--date-from",
    type=str,
    default=None,
    help="Filter by creation date (ISO format, e.g., '2024-01-01').",
)
@click.option(
    "--date-to",
    type=str,
    default=None,
    help="Filter by creation date (ISO format, e.g., '2024-12-31').",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of results to display.",
)
@click.option(
    "--page",
    type=int,
    default=1,
    help="Page number for pagination (starts at 1).",
)
@click.option(
    "--context",
    type=int,
    default=1,
    help="Number of surrounding segments to show for context.",
)
@click.option(
    "--export",
    type=click.Choice(["json", "csv", "html"], case_sensitive=False),
    default=None,
    help="Export results to file format.",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path for export (defaults to search_results.{format}).",
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def search(
    ctx: click.RichContext,
    query: str,
    podcast: Optional[str],
    speaker: Optional[str],
    backend: Optional[str],
    model: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    limit: int,
    page: int,
    context: int,
    export: Optional[str],
    output_file: Optional[Path],
    db_path: Optional[Path],
) -> None:
    """Search transcribed podcast content.

    QUERY: Search query string (FTS5 syntax supported).

    Examples:

        # Simple search
        retrocast transcription search "machine learning"

        # Search with filters
        retrocast transcription search "AI" --podcast "Tech Podcast" --limit 10

        # Search with date range
        retrocast transcription search "python" --date-from "2024-01-01" --date-to "2024-12-31"

        # Export results to JSON
        retrocast transcription search "data science" --export json --output results.json

        # Search with context and pagination
        retrocast transcription search "neural networks" --context 2 --page 2 --limit 10
    """
    from rich.markup import escape

    # Setup database
    if db_path is None:
        db_path = get_default_db_path(create=False)
        if not db_path.exists():
            console.print("[red]Database not found. Create transcriptions first.[/red]")
            ctx.exit(1)

    datastore = Datastore(db_path)

    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Perform search
    try:
        results = datastore.search_transcriptions(
            query=query,
            podcast_title=podcast,
            speaker=speaker,
            backend=backend,
            model_size=model,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            context_segments=context,
        )
    except Exception as e:
        console.print(f"[red]Search error: {e}[/red]")
        ctx.exit(1)

    if not results:
        console.print(f"\n[yellow]No results found for query: {query}[/yellow]\n")
        return

    # Handle export
    if export:
        _export_results(results, export, output_file, query)
        return

    # Display results
    console.print(
        f"\n[bold]Found {len(results)} result(s) for query: [cyan]{escape(query)}[/cyan][/bold]"
    )
    console.print(f"[dim]Page {page}, showing results {offset + 1}-{offset + len(results)}[/dim]\n")

    for i, result in enumerate(results, start=1):
        # Create separator
        console.print("─" * console.width)

        # Episode info
        console.print(
            f"[bold cyan]Result {offset + i}:[/bold cyan] "
            f"[bold]{escape(result['podcast_title'])}[/bold] - "
            f"{escape(result['episode_title'])}"
        )

        # Metadata
        metadata_parts = [f"[dim]Backend: {result['backend']}"]
        if result.get("model_size"):
            metadata_parts.append(f"Model: {result['model_size']}")
        if result.get("language"):
            metadata_parts.append(f"Language: {result['language']}")
        if result.get("created_time"):
            # Format date nicely
            date_str = result["created_time"].split("T")[0]
            metadata_parts.append(f"Created: {date_str}")
        console.print(" | ".join(metadata_parts) + "[/dim]")

        # Timestamp
        start_time = result["start_time"]
        end_time = result["end_time"]
        console.print(
            f"[dim]Time: {_format_timestamp(start_time)} - {_format_timestamp(end_time)}[/dim]"
        )

        # Context before
        if context > 0 and result.get("context_before"):
            console.print("\n[dim italic]...context...[/dim italic]")
            for ctx_seg in result["context_before"]:
                speaker_prefix = (
                    f"[Speaker {ctx_seg['speaker']}] " if ctx_seg.get("speaker") else ""
                )
                console.print(f"[dim]{speaker_prefix}{escape(ctx_seg['text'])}[/dim]")

        # Matched segment (highlighted)
        speaker_prefix = f"[Speaker {result['speaker']}] " if result.get("speaker") else ""

        # Highlight search terms in the matched text
        highlighted_text = _highlight_text(result["text"], query)
        console.print(f"\n{speaker_prefix}{highlighted_text}\n")

        # Context after
        if context > 0 and result.get("context_after"):
            for ctx_seg in result["context_after"]:
                speaker_prefix = (
                    f"[Speaker {ctx_seg['speaker']}] " if ctx_seg.get("speaker") else ""
                )
                console.print(f"[dim]{speaker_prefix}{escape(ctx_seg['text'])}[/dim]")
            console.print("[dim italic]...context...[/dim italic]")

        # File path
        console.print(f"\n[dim]File: {result['media_path']}[/dim]")

    console.print("─" * console.width)

    # Pagination hint
    if len(results) == limit:
        console.print(
            f"\n[dim]More results may be available. Use --page {page + 1} to see next page.[/dim]\n"
        )


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _highlight_text(text: str, query: str) -> Text:
    """Highlight search terms in text using Rich.

    Args:
        text: Text to highlight
        query: Search query

    Returns:
        Rich Text object with highlighted terms
    """
    # Create Rich Text object
    rich_text = Text(text)

    # Extract search terms from query (basic FTS5 parsing)
    # Remove FTS5 operators and split into words
    import re

    terms = re.findall(r"\b\w+\b", query.lower())

    # Highlight each term
    for term in terms:
        # Find all occurrences (case-insensitive)
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        for match in pattern.finditer(text):
            start, end = match.span()
            rich_text.stylize("bold yellow on blue", start, end)

    return rich_text


def _export_results(
    results: list[dict],
    format: str,
    output_file: Optional[Path],
    query: str,
) -> None:
    """Export search results to file.

    Args:
        results: List of search result dictionaries
        format: Export format (json, csv, html)
        output_file: Output file path (or None for default)
        query: Search query string
    """
    import csv
    import json
    from datetime import datetime

    # Determine output file
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"search_results_{timestamp}.{format}")

    try:
        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "query": query,
                        "timestamp": datetime.now().isoformat(),
                        "result_count": len(results),
                        "results": results,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        elif format == "csv":
            # Flatten results for CSV
            with open(output_file, "w", encoding="utf-8", newline="") as f:
                if not results:
                    return

                # CSV columns (excluding context fields)
                columns = [
                    "transcription_id",
                    "podcast_title",
                    "episode_title",
                    "media_path",
                    "language",
                    "duration",
                    "backend",
                    "model_size",
                    "created_time",
                    "segment_index",
                    "start_time",
                    "end_time",
                    "text",
                    "speaker",
                    "rank",
                ]

                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()

                for result in results:
                    # Filter out context fields for CSV
                    row = {k: v for k, v in result.items() if k in columns}
                    writer.writerow(row)

        elif format == "html":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html>\n")
                f.write("<html>\n<head>\n")
                f.write("<meta charset='utf-8'>\n")
                f.write(f"<title>Search Results: {query}</title>\n")
                f.write("<style>\n")
                f.write("""
                    body { font-family: sans-serif; margin: 2em; line-height: 1.6; }
                    h1 { color: #333; }
                    .result {
                        border: 1px solid #ddd;
                        padding: 1em;
                        margin: 1em 0;
                        border-radius: 5px;
                    }
                    .metadata { color: #666; font-size: 0.9em; }
                    .context { color: #888; font-style: italic; }
                    .match { background-color: #ff6; font-weight: bold; }
                    .timestamp { color: #666; font-family: monospace; }
                    .speaker { color: #06c; font-weight: bold; }
                """)
                f.write("</style>\n</head>\n<body>\n")
                f.write(f"<h1>Search Results: {query}</h1>\n")
                f.write(
                    f"<p class='metadata'>Generated: {datetime.now().isoformat()} | "
                    f"Results: {len(results)}</p>\n"
                )

                for i, result in enumerate(results, start=1):
                    f.write("<div class='result'>\n")
                    f.write(
                        f"<h3>Result {i}: {result['podcast_title']} - "
                        f"{result['episode_title']}</h3>\n"
                    )
                    f.write("<p class='metadata'>")
                    f.write(f"Backend: {result['backend']} | ")
                    f.write(f"Model: {result.get('model_size', 'N/A')} | ")
                    f.write(f"Language: {result.get('language', 'N/A')} | ")
                    f.write(f"Created: {result.get('created_time', 'N/A')}")
                    f.write("</p>\n")
                    f.write(
                        f"<p class='timestamp'>Time: {_format_timestamp(result['start_time'])} - "
                        f"{_format_timestamp(result['end_time'])}</p>\n"
                    )

                    # Context before
                    if result.get("context_before"):
                        f.write("<p class='context'>...context...</p>\n")
                        for ctx in result["context_before"]:
                            speaker = (
                                f"<span class='speaker'>[Speaker {ctx['speaker']}]</span> "
                                if ctx.get("speaker")
                                else ""
                            )
                            f.write(f"<p class='context'>{speaker}{ctx['text']}</p>\n")

                    # Matched text
                    speaker = (
                        f"<span class='speaker'>[Speaker {result['speaker']}]</span> "
                        if result.get("speaker")
                        else ""
                    )
                    # Simple highlighting
                    import re

                    text = result["text"]
                    terms = re.findall(r"\b\w+\b", query.lower())
                    for term in terms:
                        pattern = re.compile(re.escape(term), re.IGNORECASE)
                        text = pattern.sub(f"<span class='match'>{term}</span>", text)
                    f.write(f"<p><strong>{speaker}{text}</strong></p>\n")

                    # Context after
                    if result.get("context_after"):
                        for ctx in result["context_after"]:
                            speaker = (
                                f"<span class='speaker'>[Speaker {ctx['speaker']}]</span> "
                                if ctx.get("speaker")
                                else ""
                            )
                            f.write(f"<p class='context'>{speaker}{ctx['text']}</p>\n")
                        f.write("<p class='context'>...context...</p>\n")

                    f.write(f"<p class='metadata'>File: {result['media_path']}</p>\n")
                    f.write("</div>\n")

                f.write("</body>\n</html>\n")

        console.print(f"[green]✓[/green] Results exported to: {output_file}")

    except Exception as e:
        console.print(f"[red]Export error: {e}[/red]")


@transcription.command()
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def summary(
    ctx: click.RichContext,
    db_path: Optional[Path],
) -> None:
    """Display overall transcription statistics.

    Shows a comprehensive summary of all transcriptions in the database,
    including counts, duration, backends used, and more.

    Example:
        retrocast transcription summary
    """
    # Setup database
    if db_path is None:
        db_path = get_default_db_path(create=False)
        if not db_path.exists():
            console.print("[red]Database not found. Create transcriptions first.[/red]")
            ctx.exit(1)

    datastore = Datastore(db_path)

    # Get summary statistics
    stats = datastore.get_transcription_summary()

    if stats["total_transcriptions"] == 0:
        console.print(
            "\n[yellow]No transcriptions found in database.[/yellow]\n"
            "Use 'retrocast transcription process' to create transcriptions.\n"
        )
        return

    # Display summary
    console.print("\n[bold cyan]═══ Transcription Summary ═══[/bold cyan]\n")

    # Main stats table
    main_table = Table(show_header=False, box=None, padding=(0, 2))
    main_table.add_column("Metric", style="dim")
    main_table.add_column("Value", style="bold")

    main_table.add_row("Total Episodes Transcribed", str(stats["total_transcriptions"]))
    main_table.add_row("Unique Podcasts", str(stats["total_podcasts"]))
    main_table.add_row("Total Segments", f"{stats['total_segments']:,}")
    main_table.add_row("Total Words", f"{stats['total_words']:,}")
    main_table.add_row("Total Audio Duration", f"{stats['total_duration']:.2f} hours")
    main_table.add_row("Total Processing Time", f"{stats['total_transcription_time']:.2f} hours")

    # Date range
    if stats["date_range"][0] and stats["date_range"][1]:
        oldest = stats["date_range"][0].split("T")[0]
        newest = stats["date_range"][1].split("T")[0]
        main_table.add_row("Date Range", f"{oldest} to {newest}")

    console.print(main_table)

    # Backends breakdown
    if stats["backends_used"]:
        console.print("\n[bold]Backends Used:[/bold]")
        backend_table = Table(show_header=True, box=None, padding=(0, 2))
        backend_table.add_column("Backend", style="cyan")
        backend_table.add_column("Count", justify="right")
        for backend, count in stats["backends_used"].items():
            backend_table.add_row(backend, str(count))
        console.print(backend_table)

    # Models breakdown
    if stats["models_used"]:
        console.print("\n[bold]Models Used:[/bold]")
        model_table = Table(show_header=True, box=None, padding=(0, 2))
        model_table.add_column("Model Size", style="cyan")
        model_table.add_column("Count", justify="right")
        for model, count in stats["models_used"].items():
            model_table.add_row(model, str(count))
        console.print(model_table)

    # Languages breakdown
    if stats["languages"]:
        console.print("\n[bold]Languages:[/bold]")
        lang_table = Table(show_header=True, box=None, padding=(0, 2))
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Count", justify="right")
        for lang, count in stats["languages"].items():
            lang_table.add_row(lang, str(count))
        console.print(lang_table)

    console.print()


# Podcasts subgroup
@transcription.group(name="podcasts")
def podcasts() -> None:
    """Manage and view transcribed podcasts.

    Commands for listing and summarizing podcasts with transcriptions.
    """
    pass


@podcasts.command(name="list")
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of podcasts to display.",
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def podcasts_list(
    ctx: click.RichContext,
    limit: Optional[int],
    db_path: Optional[Path],
) -> None:
    """List all podcasts with transcriptions.

    Shows podcasts sorted by number of transcribed episodes.

    Example:
        retrocast transcription podcasts list
        retrocast transcription podcasts list --limit 10
    """
    # Setup database
    if db_path is None:
        db_path = get_default_db_path(create=False)
        if not db_path.exists():
            console.print("[red]Database not found. Create transcriptions first.[/red]")
            ctx.exit(1)

    datastore = Datastore(db_path)

    # Get podcast stats
    stats = datastore.get_podcast_transcription_stats(limit=limit)

    if not stats:
        console.print(
            "\n[yellow]No transcriptions found in database.[/yellow]\n"
            "Use 'retrocast transcription process' to create transcriptions.\n"
        )
        return

    # Display table
    console.print("\n[bold cyan]═══ Transcribed Podcasts ═══[/bold cyan]\n")

    table = Table(show_header=True)
    table.add_column("Podcast", style="cyan", no_wrap=True, max_width=40)
    table.add_column("Episodes", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Backend(s)", style="dim")

    for stat in stats:
        # Format duration as hours:minutes
        hours = int(stat["total_duration"])
        minutes = int((stat["total_duration"] % 1) * 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        table.add_row(
            stat["podcast_title"][:40],
            str(stat["episode_count"]),
            f"{stat['total_words']:,}",
            duration_str,
            stat["backends_used"],
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(stats)} podcast(s)[/dim]\n")


@podcasts.command(name="summary")
@click.argument("podcast_name", type=str, required=False)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def podcasts_summary(
    ctx: click.RichContext,
    podcast_name: Optional[str],
    db_path: Optional[Path],
) -> None:
    """Show summary statistics for podcasts.

    If PODCAST_NAME is provided, shows detailed stats for that podcast.
    Otherwise, shows overview for all podcasts.

    Examples:
        retrocast transcription podcasts summary
        retrocast transcription podcasts summary "Tech Podcast"
    """
    # Setup database
    if db_path is None:
        db_path = get_default_db_path(create=False)
        if not db_path.exists():
            console.print("[red]Database not found. Create transcriptions first.[/red]")
            ctx.exit(1)

    datastore = Datastore(db_path)

    if podcast_name:
        # Show specific podcast stats
        stats_list = datastore.get_podcast_transcription_stats()
        stat = next((s for s in stats_list if s["podcast_title"] == podcast_name), None)

        if not stat:
            console.print(
                f"\n[yellow]No transcriptions found for podcast: {podcast_name}[/yellow]\n"
            )
            # Show available podcasts
            podcasts_available = datastore.get_transcription_podcasts()
            if podcasts_available:
                console.print("[dim]Available podcasts:[/dim]")
                for p in podcasts_available[:10]:
                    console.print(f"  • {p}")
                if len(podcasts_available) > 10:
                    console.print(f"  ... and {len(podcasts_available) - 10} more")
            return

        # Display detailed stats
        console.print(f"\n[bold cyan]═══ {podcast_name} ═══[/bold cyan]\n")

        detail_table = Table(show_header=False, box=None, padding=(0, 2))
        detail_table.add_column("Metric", style="dim")
        detail_table.add_column("Value", style="bold")

        detail_table.add_row("Episodes Transcribed", str(stat["episode_count"]))
        detail_table.add_row("Total Segments", f"{stat['total_segments']:,}")
        detail_table.add_row("Total Words", f"{stat['total_words']:,}")
        detail_table.add_row("Total Duration", f"{stat['total_duration']:.2f} hours")
        detail_table.add_row("Processing Time", f"{stat['total_transcription_time']:.2f} hours")
        detail_table.add_row("Backends Used", stat["backends_used"])
        detail_table.add_row("Models Used", stat["models_used"])

        if stat["date_range"][0] and stat["date_range"][1]:
            oldest = stat["date_range"][0].split("T")[0]
            newest = stat["date_range"][1].split("T")[0]
            detail_table.add_row("Date Range", f"{oldest} to {newest}")

        console.print(detail_table)
        console.print()

    else:
        # Show overview for all podcasts
        stats = datastore.get_podcast_transcription_stats()

        if not stats:
            console.print(
                "\n[yellow]No transcriptions found in database.[/yellow]\n"
                "Use 'retrocast transcription process' to create transcriptions.\n"
            )
            return

        console.print("\n[bold cyan]═══ Podcast Summary ═══[/bold cyan]\n")

        # Summary table
        summary_table = Table(show_header=True)
        summary_table.add_column("Podcast", style="cyan", max_width=35)
        summary_table.add_column("Episodes", justify="right")
        summary_table.add_column("Segments", justify="right")
        summary_table.add_column("Words", justify="right")
        summary_table.add_column("Duration (h)", justify="right")
        summary_table.add_column("Proc. Time (h)", justify="right")

        total_episodes = 0
        total_segments = 0
        total_words = 0
        total_duration = 0.0
        total_proc_time = 0.0

        for stat in stats:
            summary_table.add_row(
                stat["podcast_title"][:35],
                str(stat["episode_count"]),
                f"{stat['total_segments']:,}",
                f"{stat['total_words']:,}",
                f"{stat['total_duration']:.2f}",
                f"{stat['total_transcription_time']:.2f}",
            )
            total_episodes += stat["episode_count"]
            total_segments += stat["total_segments"]
            total_words += stat["total_words"]
            total_duration += stat["total_duration"]
            total_proc_time += stat["total_transcription_time"]

        console.print(summary_table)

        # Totals
        console.print(
            f"\n[bold]Totals:[/bold] {len(stats)} podcasts, "
            f"{total_episodes} episodes, {total_segments:,} segments, "
            f"{total_words:,} words, {total_duration:.2f}h audio, "
            f"{total_proc_time:.2f}h processing\n"
        )


# Episodes subgroup
@transcription.group(name="episodes")
def episodes() -> None:
    """Manage and view transcribed episodes.

    Commands for listing and summarizing episodes with transcriptions.
    """
    pass


@episodes.command(name="list")
@click.option(
    "--podcast",
    type=str,
    default=None,
    help="Filter by podcast title.",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of episodes to display.",
)
@click.option(
    "--page",
    type=int,
    default=1,
    help="Page number for pagination.",
)
@click.option(
    "--order",
    type=click.Choice(["date", "duration", "words", "title"], case_sensitive=False),
    default="date",
    help="Sort order for results.",
)
@click.option(
    "--asc",
    is_flag=True,
    help="Sort in ascending order (default is descending).",
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def episodes_list(
    ctx: click.RichContext,
    podcast: Optional[str],
    limit: int,
    page: int,
    order: str,
    asc: bool,
    db_path: Optional[Path],
) -> None:
    """List transcribed episodes.

    Shows episodes sorted by the specified order (default: most recent first).

    Examples:
        retrocast transcription episodes list
        retrocast transcription episodes list --podcast "Tech Podcast"
        retrocast transcription episodes list --order duration --limit 10
    """
    # Setup database
    if db_path is None:
        db_path = get_default_db_path(create=False)
        if not db_path.exists():
            console.print("[red]Database not found. Create transcriptions first.[/red]")
            ctx.exit(1)

    datastore = Datastore(db_path)

    # Map order option to column name
    order_map = {
        "date": "created_time",
        "duration": "duration",
        "words": "word_count",
        "title": "episode_title",
    }
    order_by = order_map.get(order, "created_time")

    # Calculate offset
    offset = (page - 1) * limit

    # Get episodes
    episodes_data = datastore.get_episode_transcription_list(
        podcast_title=podcast,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_desc=not asc,
    )

    if not episodes_data:
        if podcast:
            console.print(f"\n[yellow]No transcriptions found for podcast: {podcast}[/yellow]\n")
        else:
            console.print(
                "\n[yellow]No transcriptions found in database.[/yellow]\n"
                "Use 'retrocast transcription process' to create transcriptions.\n"
            )
        return

    # Get total count for pagination
    total_count = datastore.count_transcriptions(podcast_title=podcast)

    # Display table
    title = "Transcribed Episodes"
    if podcast:
        title += f" - {podcast}"
    console.print(f"\n[bold cyan]═══ {title} ═══[/bold cyan]\n")

    table = Table(show_header=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Episode", style="cyan", max_width=40)
    if not podcast:
        table.add_column("Podcast", style="dim", max_width=25)
    table.add_column("Duration", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Language", justify="center")
    table.add_column("Date", style="dim")

    for i, ep in enumerate(episodes_data, start=offset + 1):
        # Format duration as MM:SS or HH:MM:SS
        duration = ep["duration"] or 0
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        secs = int(duration % 60)
        if hours > 0:
            duration_str = f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            duration_str = f"{minutes}:{secs:02d}"

        # Format date
        date_str = ep["created_time"].split("T")[0] if ep.get("created_time") else "N/A"

        row = [
            str(i),
            ep["episode_title"][:40] if ep.get("episode_title") else "Unknown",
        ]
        if not podcast:
            row.append(ep["podcast_title"][:25] if ep.get("podcast_title") else "Unknown")
        row.extend(
            [
                duration_str,
                f"{ep['word_count']:,}" if ep.get("word_count") else "0",
                ep.get("language") or "N/A",
                date_str,
            ]
        )

        table.add_row(*row)

    console.print(table)

    # Pagination info
    start_num = offset + 1
    end_num = min(offset + len(episodes_data), total_count)
    console.print(
        f"\n[dim]Showing {start_num}-{end_num} of {total_count} episodes (page {page})[/dim]"
    )

    if end_num < total_count:
        console.print(f"[dim]Use --page {page + 1} for next page[/dim]")
    console.print()


@episodes.command(name="summary")
@click.option(
    "--podcast",
    type=str,
    default=None,
    help="Filter by podcast title.",
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def episodes_summary(
    ctx: click.RichContext,
    podcast: Optional[str],
    db_path: Optional[Path],
) -> None:
    """Show summary statistics for transcribed episodes.

    Displays aggregate statistics about transcribed episodes.

    Examples:
        retrocast transcription episodes summary
        retrocast transcription episodes summary --podcast "Tech Podcast"
    """
    # Setup database
    if db_path is None:
        db_path = get_default_db_path(create=False)
        if not db_path.exists():
            console.print("[red]Database not found. Create transcriptions first.[/red]")
            ctx.exit(1)

    datastore = Datastore(db_path)

    # Get episodes
    episodes_data = datastore.get_episode_transcription_list(
        podcast_title=podcast,
        limit=None,  # Get all for summary
    )

    if not episodes_data:
        if podcast:
            console.print(f"\n[yellow]No transcriptions found for podcast: {podcast}[/yellow]\n")
        else:
            console.print(
                "\n[yellow]No transcriptions found in database.[/yellow]\n"
                "Use 'retrocast transcription process' to create transcriptions.\n"
            )
        return

    # Calculate statistics
    total_episodes = len(episodes_data)
    total_duration = sum(ep.get("duration") or 0 for ep in episodes_data)
    total_words = sum(ep.get("word_count") or 0 for ep in episodes_data)
    total_proc_time = sum(ep.get("transcription_time") or 0 for ep in episodes_data)

    # Calculate averages
    avg_duration = total_duration / total_episodes if total_episodes > 0 else 0
    avg_words = total_words / total_episodes if total_episodes > 0 else 0
    avg_proc_time = total_proc_time / total_episodes if total_episodes > 0 else 0

    # Find min/max durations
    durations = [ep.get("duration") or 0 for ep in episodes_data]
    min_duration = min(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    # Language distribution
    languages: dict[str, int] = {}
    for ep in episodes_data:
        lang = ep.get("language") or "unknown"
        languages[lang] = languages.get(lang, 0) + 1

    # Display summary
    title = "Episode Summary"
    if podcast:
        title += f" - {podcast}"
    console.print(f"\n[bold cyan]═══ {title} ═══[/bold cyan]\n")

    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column("Metric", style="dim")
    stats_table.add_column("Value", style="bold")

    stats_table.add_row("Total Episodes", str(total_episodes))
    stats_table.add_row("Total Duration", f"{total_duration / 3600:.2f} hours")
    stats_table.add_row("Total Words", f"{total_words:,}")
    stats_table.add_row("Total Processing Time", f"{total_proc_time / 3600:.2f} hours")
    stats_table.add_row("", "")
    stats_table.add_row("Average Duration", f"{avg_duration / 60:.1f} minutes")
    stats_table.add_row("Average Words", f"{avg_words:,.0f}")
    stats_table.add_row("Average Processing Time", f"{avg_proc_time:.1f} seconds")
    stats_table.add_row("", "")
    stats_table.add_row("Shortest Episode", f"{min_duration / 60:.1f} minutes")
    stats_table.add_row("Longest Episode", f"{max_duration / 60:.1f} minutes")

    console.print(stats_table)

    # Language breakdown
    if languages:
        console.print("\n[bold]Languages:[/bold]")
        lang_table = Table(show_header=True, box=None, padding=(0, 2))
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Episodes", justify="right")
        lang_table.add_column("Percentage", justify="right")

        for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
            pct = (count / total_episodes) * 100
            lang_table.add_row(lang, str(count), f"{pct:.1f}%")

        console.print(lang_table)

    console.print()
