"""Crawl-related CLI commands."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

# import click
import rich_click as click
from rich.console import Console
from rich.table import Table

from retrocast.aria_downloader import AriaDownloader
from retrocast.logging_config import get_logger, setup_logging

console = Console()
stderr_console = Console(stderr=True)


@click.group()
@click.pass_context
def download(ctx: click.RichContext) -> None:
    """Download episode content with pluggable backends"""

    ctx.ensure_object(dict)


def _read_urls_from_source(filename: str) -> tuple[list[str], list[str]]:
    if filename == "-":
        lines = [line.rstrip("\n") for line in sys.stdin]
    else:
        path = Path(filename)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

    urls: list[str] = []
    skipped: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parsed = urlparse(line)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            urls.append(line)
        else:
            skipped.append(line)
    return urls, skipped


@download.command()
@click.argument("filename", required=False, default="-")
@click.option(
    "-d",
    "--directory",
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    default=Path.cwd(),
    show_default=True,
    help="Directory to store downloaded files.",
)
@click.option(
    "-j",
    "--max-concurrent",
    type=click.IntRange(min=1),
    default=5,
    show_default=True,
    help="Maximum concurrent aria2c downloads.",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging for this command.")
@click.option("--secret", type=str, default=None, help="RPC secret token for aria2c.")
@click.pass_context
def aria(
    ctx: click.RichContext,
    filename: str,
    directory: Path,
    max_concurrent: int,
    verbose: bool,
    secret: str | None,
) -> None:
    """Download URLs using the aria2c fetcher."""

    ctx.ensure_object(dict)
    base_verbose = ctx.obj.get("verbose", False)
    log_file = ctx.obj.get("log_file")
    app_dir = ctx.obj.get("app_dir", Path.cwd())
    if verbose and not base_verbose:
        setup_logging(app_dir, log_file=log_file)
        ctx.obj["verbose"] = True

    logger = get_logger("retrocast.download.aria")

    try:
        urls, skipped = _read_urls_from_source(filename)
    except FileNotFoundError:
        stderr_console.print(f"[red]URL file not found:[/red] {filename}")
        ctx.exit(1)
    except OSError as exc:
        stderr_console.print(f"[red]Failed to read URL source:[/red] {exc}")
        ctx.exit(1)

    if skipped:
        logger.warning("Skipped {} invalid URL entries", len(skipped))

    if not urls:
        console.print("[yellow]No valid URLs provided; nothing to download.[/yellow]")
        return

    directory.mkdir(parents=True, exist_ok=True)
    downloader = AriaDownloader(
        directory=directory,
        max_concurrent=max_concurrent,
        secret=secret,
        verbose=verbose or base_verbose,
    )

    logger.info("Starting aria2 download session with {} URLs", len(urls))

    try:
        downloader.start()
        downloader.add_urls(urls)
        completed, failed = downloader.wait_for_completion()
    except RuntimeError as exc:
        stderr_console.print(f"[red]aria2 download session failed:[/red] {exc}")
        logger.error("aria2 download session failed: {}", exc)
        ctx.exit(1)
    except KeyboardInterrupt:
        stderr_console.print("[yellow]Interrupted by user, stopping downloads...[/yellow]")
        logger.warning("Download session interrupted by user")
        completed, failed = downloader.get_results()
    finally:
        downloader.stop()

    _render_summary(completed, failed)


def _render_summary(
    completed: Iterable[dict],
    failed: Iterable[dict],
) -> None:
    completed_list = list(completed)
    failed_list = list(failed)

    table = Table(title="aria2 Download Summary", show_lines=False)
    table.add_column("Status", style="bold")
    table.add_column("File")
    table.add_column("Size", justify="right")
    table.add_column("Message")

    for record in completed_list:
        size = _format_size(record.get("completedLength", "0"))
        table.add_row("[green]Complete[/green]", _display_name(record), size, "")

    for record in failed_list:
        size = _format_size(record.get("completedLength", "0"))
        message = record.get("errorMessage") or f"Error code {record.get('errorCode')}"
        table.add_row("[red]Failed[/red]", _display_name(record), size, message)

    console.print(table)
    console.print(
        f"Completed: [green]{len(completed_list)}[/green]  "
        f"Failed: [red]{len(failed_list)}[/red]"
    )


def _display_name(record: dict) -> str:
    path = record.get("path")
    if path:
        return Path(path).name
    return record.get("gid", "unknown")


def _format_size(size_value: str | None) -> str:
    try:
        size_int = int(size_value or "0")
    except ValueError:
        return "-"

    if size_int <= 0:
        return "-"

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_int)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    return f"{value:.2f} {units[unit_index]}"


__all__ = ["download"]
