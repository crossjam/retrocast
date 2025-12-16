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

from retrocast.appdir import get_app_dir
from retrocast.datastore import Datastore
from retrocast.transcription import TranscriptionManager

console = Console()

# Supported audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac", ".aac"}


@click.group(name="process")
@click.pass_context
def process(ctx: click.RichContext) -> None:
    """Process podcast audio files (transcription, analysis)."""
    ctx.ensure_object(dict)


@process.command()
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
    required=True,
)
@click.option(
    "--backend",
    type=click.Choice(["auto", "mlx-whisper"], case_sensitive=False),
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
    help="Path to database file (defaults to app_dir/overcast.db).",
)
@click.pass_context
def transcribe(
    ctx: click.RichContext,
    paths: tuple[Path, ...],
    backend: str,
    model: str,
    language: Optional[str],
    output_dir: Optional[Path],
    output_format: str,
    force: bool,
    db_path: Optional[Path],
) -> None:
    """Transcribe audio files to text.

    PATHS: One or more audio files or directories containing audio files.

    Examples:

        # Transcribe a single file
        retrocast process transcribe episode.mp3

        # Transcribe all files in a directory
        retrocast process transcribe /path/to/podcast/

        # Use specific backend and model
        retrocast process transcribe --backend mlx-whisper --model medium file.mp3

        # Save as SRT subtitle format
        retrocast process transcribe --format srt episode.mp3
    """
    # Setup
    app_dir = get_app_dir(create=True)
    if output_dir is None:
        output_dir = app_dir / "transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    if db_path is None:
        db_path = app_dir / "overcast.db"

    # Initialize datastore
    datastore = Datastore(db_path)

    # Collect audio files
    audio_files = []
    for path in paths:
        if path.is_file():
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                audio_files.append(path)
            else:
                console.print(
                    f"[yellow]Skipping {path.name}: not a supported audio file[/yellow]"
                )
        elif path.is_dir():
            # Find all audio files in directory
            for ext in AUDIO_EXTENSIONS:
                audio_files.extend(path.rglob(f"*{ext}"))
        else:
            console.print(f"[yellow]Skipping {path}: not a file or directory[/yellow]")

    if not audio_files:
        console.print("[red]No audio files found to transcribe.[/red]")
        ctx.exit(1)

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

    # Temporarily suppress INFO logs during transcription to avoid cluttering progress
    from loguru import logger

    logger_id = logger.add(lambda _: None, level="WARNING", filter=lambda r: True)

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
                    # Transcribe
                    result = manager.transcribe_file(
                        audio_path=audio_file,
                        podcast_title=audio_file.parent.name,
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
        logger.remove(logger_id)


@process.command(name="list-backends")
def list_backends() -> None:
    """List available transcription backends.

    Shows which backends are installed and available on your system.
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


@process.command(name="test-backend")
@click.argument("backend_name", type=str)
def test_backend(backend_name: str) -> None:
    """Test if a specific backend is available.

    BACKEND_NAME: Name of backend to test (e.g., 'mlx-whisper')

    Example:
        retrocast process test-backend mlx-whisper
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


@process.command(name="search")
@click.argument("query", type=str)
@click.option(
    "--podcast",
    type=str,
    default=None,
    help="Filter by podcast title.",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Maximum number of results to show.",
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to database file (defaults to app_dir/overcast.db).",
)
def search(
    query: str,
    podcast: Optional[str],
    limit: int,
    db_path: Optional[Path],
) -> None:
    """Search transcribed content.

    QUERY: Search query (supports full-text search)

    Examples:

        # Search all transcriptions
        retrocast process search "machine learning"

        # Search within a specific podcast
        retrocast process search --podcast "My Podcast" "episode topic"

        # Limit results
        retrocast process search --limit 5 "python"
    """
    # Setup
    app_dir = get_app_dir(create=True)
    if db_path is None:
        db_path = app_dir / "overcast.db"

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/red]")
        console.print("\nNo transcriptions exist yet. Transcribe some audio files first.")
        return

    # Initialize datastore
    datastore = Datastore(db_path)

    # Search
    try:
        results = datastore.search_transcriptions(
            query=query,
            podcast_title=podcast,
            limit=limit,
        )
    except Exception as e:
        console.print(f"[red]Search error: {e}[/red]")
        return

    if not results:
        console.print(f"\n[yellow]No results found for: {query}[/yellow]\n")
        return

    # Display results
    console.print(f"\n[bold]Found {len(results)} result(s) for: {query}[/bold]\n")

    for i, result in enumerate(results, 1):
        podcast_title = result.get("podcast_title", "Unknown")
        episode_title = result.get("episode_title", "Unknown")
        text = result.get("text", "")
        start_time = result.get("start_time", 0)

        # Format timestamp
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"

        console.print(f"[bold cyan]{i}. {podcast_title} - {episode_title}[/bold cyan]")
        console.print(f"   [dim]Time: {timestamp}[/dim]")
        console.print(f"   {text}\n")
