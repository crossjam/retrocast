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
    help="Path to database file (defaults to app_dir/retrocast.db).",
)
@click.pass_context
def process_audio(
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
    """Process audio files to create transcriptions.

    PATHS: One or more audio files or directories containing audio files.

    Examples:

        # Process a single file
        retrocast transcription process episode.mp3

        # Process all files in a directory
        retrocast transcription process /path/to/podcast/

        # Use specific backend and model
        retrocast transcription process --backend mlx-whisper --model medium file.mp3

        # Save as SRT subtitle format
        retrocast transcription process --format srt episode.mp3
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
        logger.enable("retrocast")


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
            f"\n[dim]More results may be available. "
            f"Use --page {page + 1} to see next page.[/dim]\n"
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

    terms = re.findall(r'\b\w+\b', query.lower())

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
                    terms = re.findall(r'\b\w+\b', query.lower())
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
