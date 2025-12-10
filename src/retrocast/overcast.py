import csv
import json
import os
import sys
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import click
import requests
from requests import Session
from rich.console import Console
from rich.table import Table

from .appdir import ensure_app_dir, get_auth_path, get_default_db_path
from .chapters_backfill import backfill_all_chapters
from .constants import (
    BATCH_SIZE,
    ENCLOSURE_URL,
    INCLUDE_PODCAST_IDS,
    OVERCAST_ID,
    SMART,
    SORTING,
    TITLE,
    USER_REC_DATE,
)
from .datastore import Datastore
from .exceptions import AuthFailedError, OpmlFetchError, WrongPasswordError
from .feed import fetch_xml_and_extract
from .html.page import generate_html_played
from .logging_config import get_logger
from .utils import (
    _archive_path,
    _file_extension_for_type,
    _headers_ua,
    _parse_date_or_none,
    _sanitize_for_path,
)

logger = get_logger(__name__)


def auth_and_save_cookies(email: str, password: str, auth_json: str) -> None:
    """Authenticate to Overcast and save cookies to a JSON file."""
    session = Session()
    response = session.post(
        "https://overcast.fm/login?then=account",
        data={"email": email, "password": password},
        allow_redirects=False,
    )

    if "Incorrect password" in response.text:
        raise WrongPasswordError
    cookies = session.cookies.get_dict()
    if "o" not in cookies:
        raise AuthFailedError

    logger.info("Authenticated successfully. Saving session.")
    auth_json_path = Path(auth_json)
    if auth_json_path.exists():
        auth_data = json.loads(auth_json_path.read_text())
    else:
        auth_data = {}
    auth_data["overcast"] = cookies
    auth_json_path.write_text(json.dumps(auth_data, indent=4) + "\n")


def _session_from_json(auth_json_path: str) -> Session:
    with Path(auth_json_path).open() as f:
        cookies = json.load(f)["overcast"]
        session = Session()
        session.cookies.update(cookies)
        return session


def _session_from_cookie(cookie: str) -> Session:
    session = Session()
    session.cookies.update({"o": cookie, "qr": "-"})
    return session


def fetch_opml(session: Session, archive_dir: Path | None) -> str:
    """Fetch OPML from Overcast and optionally save OPML to an archive directory."""
    response = session.get(
        "https://overcast.fm/account/export_opml/extended",
        timeout=None,
    )
    if not response.ok:
        raise OpmlFetchError(dict(response.headers))
    response_text = response.text
    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        now = int(datetime.now(tz=UTC).timestamp())
        archive_dir.joinpath(f"overcast-{now}.opml").write_text(response_text)
    return response_text


def _iso_date_or_none(dictionary: dict, key: str) -> str | None:
    if key in dictionary:
        return _parse_date_or_none(dictionary[key])
    return None


def extract_playlists_from_opml(root: Element) -> Iterable[dict]:
    for playlist in root.findall(
        "./body/outline[@text='playlists']/outline[@type='podcast-playlist']",
    ):
        if INCLUDE_PODCAST_IDS in playlist.attrib:
            yield {
                TITLE: playlist.attrib[TITLE],
                SMART: int(playlist.attrib[SMART]),
                SORTING: playlist.attrib[SORTING],
                INCLUDE_PODCAST_IDS: f"[{playlist.attrib[INCLUDE_PODCAST_IDS]}]",
            }


def extract_feed_and_episodes_from_opml(
    root: Element,
) -> Iterable[tuple[dict, list[dict]]]:
    for feed in root.findall("./body/outline[@text='feeds']/outline[@type='rss']"):
        episodes = []
        feed_attrs = cast(dict[str, Any], feed.attrib.copy())
        feed_attrs[OVERCAST_ID] = int(feed_attrs[OVERCAST_ID])
        feed_attrs["subscribed"] = feed_attrs.get("subscribed", False) == "1"
        feed_attrs["notifications"] = feed_attrs.get("notifications", False) == "1"
        feed_attrs["overcastAddedDate"] = _iso_date_or_none(
            feed_attrs,
            "overcastAddedDate",
        )
        del feed_attrs["type"]
        del feed_attrs["text"]

        for episode_xml in feed.findall("./outline[@type='podcast-episode']"):
            ep_attrs = cast(dict[str, Any], episode_xml.attrib.copy())
            ep_attrs[OVERCAST_ID] = int(ep_attrs[OVERCAST_ID])
            ep_attrs[ENCLOSURE_URL] = ep_attrs[ENCLOSURE_URL].split("?")[0]

            ep_attrs["feedId"] = feed_attrs["overcastId"]
            ep_attrs["played"] = ep_attrs.get("played", False) == "1"
            ep_attrs["userDeleted"] = ep_attrs.get("userDeleted", False) == "1"
            ep_attrs["progress"] = (
                None if (progress := ep_attrs.get("progress")) is None else int(progress)
            )
            ep_attrs["userUpdatedDate"] = _iso_date_or_none(ep_attrs, "userUpdatedDate")
            ep_attrs[USER_REC_DATE] = _iso_date_or_none(
                ep_attrs,
                USER_REC_DATE,
            )
            ep_attrs["pubDate"] = _iso_date_or_none(ep_attrs, "pubDate")
            del ep_attrs["type"]

            episodes.append(ep_attrs)

        yield feed_attrs, episodes


# CLI Helper Functions


def _ensure_app_dir_from_ctx(ctx: click.Context) -> Path:
    """Ensure the application directory exists and update the context."""

    app_dir = ctx.obj.get("app_dir")
    if app_dir is None or not Path(app_dir).exists():
        app_dir = ensure_app_dir()
        ctx.obj["app_dir"] = app_dir
    return Path(app_dir)


def _resolve_db_path(ctx: click.Context, db_path: str | None) -> Path:
    """Resolve a database path relative to the application directory."""

    app_dir = _ensure_app_dir_from_ctx(ctx)

    if db_path is None:
        resolved_db_path: Path = get_default_db_path(create=True)
    elif not Path(db_path).is_absolute():
        resolved_db_path = app_dir / db_path
    else:
        resolved_db_path = Path(db_path)

    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_db_path


def _confirm_db_creation(db_path: Path | str) -> bool:
    """Confirm database creation if it doesn't exist."""
    if Datastore.exists(db_path):
        return True

    return click.confirm(
        f"Database file '{db_path}' does not exist. Create it?",
        default=True,
    )


def _auth_and_fetch(auth_path: str | None, archive: Path | None) -> str:
    if (cookie := os.getenv("OVERCAST_COOKIE")) is not None:
        session = _session_from_cookie(cookie)
    else:
        actual_auth_path = auth_path if auth_path else str(get_auth_path())
        if not Path(actual_auth_path).exists():
            click.echo(f"Auth file not found at {actual_auth_path}")
            ctx = click.get_current_context()
            ctx.invoke(auth)
        session = _session_from_json(actual_auth_path)
    return fetch_opml(session, archive)


# CLI Commands


@click.group()
@click.pass_context
def overcast(ctx: click.Context) -> None:
    """Synchronize subscription metadata via overcast plugin"""
    pass


@overcast.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize Overcast database in user platform directory."""
    console = Console()
    app_dir = _ensure_app_dir_from_ctx(ctx)
    db_path = get_default_db_path(create=True)

    # Check if database already exists
    already_exists = Datastore.exists(db_path)

    console.print()
    console.print("[bold cyan]Overcast Database Initialization[/bold cyan]")
    console.print()

    # Create status table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")

    table.add_row("Config directory:", str(app_dir))
    table.add_row("Database path:", str(db_path))

    if already_exists:
        table.add_row("Status:", "[yellow]✓ Already exists[/yellow]")
    else:
        # Create the database by instantiating Datastore
        table.add_row("Status:", "[green]✓ Created[/green]")

    console.print(table)
    console.print()

    if not already_exists:
        console.print("[dim]Database schema initialized successfully.[/dim]")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print("  1. Authenticate:  [cyan]retrocast sync overcast auth[/cyan]")
        console.print("  2. Sync data:     [cyan]retrocast sync overcast save[/cyan]")
        console.print("  3. Download:     [cyan]retrocast retrieve overcast transcripts[/cyan]")
        console.print()
    else:
        console.print("[dim]Use [cyan]retrocast sync overcast check[/cyan] to verify setup.[/dim]")
        console.print()


@overcast.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Check authentication and database setup status."""
    console = Console()
    app_dir = Path(ctx.obj["app_dir"])
    app_exists = app_dir.exists()

    # Check auth file
    auth_path = get_auth_path()
    auth_exists = auth_path.exists() if app_exists else False

    # Check database
    db_path = get_default_db_path()
    db_exists = Datastore.exists(db_path) if app_exists else False

    # Create status table
    table = Table(title="Retrocast Setup Status", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="bold")
    table.add_column("Path", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Action", style="dim italic")

    # Add app directory row
    table.add_row(
        "App Directory",
        str(app_dir),
        "[green]✓[/green]" if app_exists else "[red]✗ Missing[/red]",
        "" if app_exists else "Run: retrocast config initialize",
    )

    # Add auth row
    if auth_exists:
        table.add_row("Auth File", str(auth_path), "[green]✓ Found[/green]", "")
    else:
        table.add_row(
            "Auth File",
            str(auth_path),
            "[red]✗ Not found[/red]",
            "Run: retrocast sync overcast auth",
        )

    # Add database row
    if db_exists:
        table.add_row("Database", str(db_path), "[green]✓ Found[/green]", "")
    else:
        table.add_row(
            "Database",
            str(db_path),
            "[red]✗ Not found[/red]",
            "Run: retrocast sync overcast save",
        )

    console.print()
    console.print(table)
    console.print()

    if auth_exists and db_exists:
        console.print("[bold green]✓ All setup complete![/bold green]")
        sys.exit(0)
    else:
        console.print("[bold red]✗ Setup incomplete[/bold red]")
        sys.exit(1)


@overcast.command()
@click.pass_context
@click.option(
    "-a",
    "--auth",
    "custom_auth_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Custom path to save auth cookie (defaults to app directory)",
)
@click.option(
    "--email",
    prompt=True,
    hide_input=False,
)
@click.password_option()
def auth(ctx: click.Context, custom_auth_path: str | None, email: str, password: str) -> None:
    """Save authentication credentials to a JSON file."""
    _ensure_app_dir_from_ctx(ctx)
    auth_path = custom_auth_path if custom_auth_path else str(get_auth_path(create=True))
    click.echo("Logging in to Overcast")
    click.echo(
        f"Your password is not stored but an auth cookie will be saved to {auth_path}",
    )
    click.echo()
    auth_and_save_cookies(email, password, auth_path)


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option(
    "-a",
    "--auth",
    "custom_auth_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    help="Custom path to auth.json file (defaults to app directory)",
)
@click.option(
    "--load",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    help="Load OPML from this file instead of the API",
)
@click.option("-na", "--no-archive", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def save(
    ctx: click.Context,
    db_path: str | None,
    custom_auth_path: str | None,
    load: str | None,
    no_archive: bool,
    verbose: bool,
) -> None:
    """Save Overcast info to SQLite database."""

    resolved_db_path = _resolve_db_path(ctx, db_path)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(resolved_db_path)
    ingested_feed_ids = set()
    if load:
        xml = Path(load).read_text()
    else:
        logger.info("🔉 Fetching latest OPML from Overcast")
        xml = _auth_and_fetch(
            custom_auth_path,
            None if no_archive else _archive_path(resolved_db_path, "retrocast"),
        )

    if verbose:
        logger.info("📥 Parsing OPML...")
    root = ElementTree.fromstring(xml)

    for playlist in extract_playlists_from_opml(root):
        if verbose:
            logger.info("▶️ Saving playlist: {title}", title=playlist["title"])
        db.save_playlist(playlist)

    for feed, episodes in extract_feed_and_episodes_from_opml(root):
        if not episodes:
            if verbose:
                logger.warning("⚠️ Skipping %s (no episodes)", feed[TITLE])
            continue
        if verbose:
            logger.info(
                "⤵️ Saving %s (latest: %s)",
                feed[TITLE],
                episodes[0][TITLE],
            )
        ingested_feed_ids.add(feed["overcastId"])
        db.save_feed_and_episodes(feed, episodes)

    db.mark_feed_removed_if_missing(ingested_feed_ids)


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option("-na", "--no-archive", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def extend(
    ctx: click.Context,
    db_path: str | None,
    no_archive: bool,
    verbose: bool,
) -> None:
    """Download XML feed and extract all feed and episode tags and attributes."""

    resolved_db_path = _resolve_db_path(ctx, db_path)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(resolved_db_path)
    feeds_to_extend = db.get_feeds_to_extend()
    logger.info("➡️ Extending %d feeds", len(feeds_to_extend))

    archive_dir = None if no_archive else _archive_path(resolved_db_path, "feeds")

    def _fetch_feed_extend_save(feed_url: tuple[str, str]) -> tuple[dict, list[dict]]:
        feed_title, url = feed_url
        title = _sanitize_for_path(feed_title)
        feed, episodes, chapters = fetch_xml_and_extract(
            xml_url=url,
            title=title,
            archive_dir=archive_dir,
            verbose=verbose,
            headers=_headers_ua(),
        )
        if not episodes:
            if verbose:
                logger.warning("⚠️ Skipping %s (no episodes)", title)
        else:
            if verbose:
                logger.info("⏩️ Extending %s (latest: %s)", title, episodes[0][TITLE])
            if "errorCode" in feed:
                logger.error("⛔️ Found error: %s", feed["errorCode"])
        return feed, episodes

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        results = list(executor.map(_fetch_feed_extend_save, feeds_to_extend))

    if verbose:
        logger.info("Saving %d feeds to database", len(results))
    for feed, episodes in results:
        db.save_extended_feed_and_episodes(feed, episodes)


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option(
    "-p",
    "--path",
    "archive_path",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
)
@click.option("-s", "--starred-only", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def transcripts(  # noqa: C901
    ctx: click.Context,
    db_path: str | None,
    archive_path: str | None,
    starred_only: bool,
    verbose: bool,
) -> None:
    """Download available transcripts for all or starred episodes."""

    if ctx.command_path.startswith("retrocast sync"):
        Console(stderr=True).print(
            "[yellow]Use `retrocast retrieve overcast transcripts` for future runs."
            " The current location will be deprecated.[/yellow]",
        )

    resolved_db_path = _resolve_db_path(ctx, db_path)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(resolved_db_path)

    transcripts_path = (
        Path(archive_path) if archive_path else _archive_path(resolved_db_path, "transcripts")
    )

    transcripts_path.mkdir(parents=True, exist_ok=True)

    if db.ensure_transcript_columns():
        logger.warning("⚠️ No transcript URLs found in database, please run `extend`")

    transcripts_to_download = list(
        db.transcripts_to_download(starred_only=starred_only),
    )

    if verbose:
        logger.info("🔉 Downloading %d transcripts...", len(transcripts_to_download))

    def _fetch_and_write_transcript(
        transcript: tuple[str, str, str, str, str],
    ) -> tuple[str, str] | None:
        title, url, mimetype, enclosure, feed_title = transcript
        if verbose:
            logger.info("⬇️ Downloading %s @ %s", title, url)
        try:
            response = requests.get(url, headers=_headers_ua())
        except requests.exceptions.RequestException as e:
            logger.error("⛔ Error downloading %s: %s", url, e)
            return None

        if not response.ok:
            logger.error("⛔ Error code %s downloading %s", response.status_code, url)
            if verbose:
                logger.debug("Response headers: %s", response.headers)
            return None
        feed_path = transcripts_path / _sanitize_for_path(feed_title)
        feed_path.mkdir(exist_ok=True)
        file_ext = _file_extension_for_type(response.headers, mimetype)
        file_path = feed_path / (_sanitize_for_path(title) + file_ext)
        if verbose:
            logger.info("📝 Saving %s", file_path)
        with file_path.open(mode="wb") as file:
            file.write(response.content)
        return enclosure, str(file_path.absolute())

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        results = list(
            executor.map(_fetch_and_write_transcript, transcripts_to_download),
        )

    if verbose:
        logger.info("Saving %d transcripts to database", len(results))
    for row in results:
        if row is not None:
            enclosure, file_path = row
            db.update_transcript_download_paths(
                enclosure,
                str(file_path),
            )


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option(
    "-p",
    "--path",
    "archive_path",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
)
def chapters(
    ctx: click.Context,
    db_path: str | None,
    archive_path: str | None,
) -> None:
    """Download and store available chapters for all or starred episodes."""

    if ctx.command_path.startswith("retrocast sync"):
        Console(stderr=True).print(
            "[yellow]Use `retrocast retrieve overcast chapters` for future runs."
            " The current location will be deprecated.[/yellow]",
        )

    resolved_db_path = _resolve_db_path(ctx, db_path)
    app_dir = _ensure_app_dir_from_ctx(ctx)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    archive_root = Path(archive_path) if archive_path else app_dir / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    backfill_all_chapters(resolved_db_path, archive_root)


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
)
def html(
    ctx: click.Context,
    db_path: str | None,
    output_path: str | None,
) -> None:
    """Download and store available chapters for all or starred episodes."""

    resolved_db_path = _resolve_db_path(ctx, db_path)
    app_dir = _ensure_app_dir_from_ctx(ctx)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    if output_path:
        if Path(output_path).is_dir():
            html_output_path = Path(output_path) / "overcast-played.html"
        else:
            html_output_path = Path(output_path)
    else:
        html_output_path = app_dir / "retrocast-played.html"
    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_html_played(resolved_db_path, html_output_path)
    logger.info("📝 Saved HTML to: file://%s", html_output_path.absolute())


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.argument("feed_titles", nargs=-1, required=False)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    help="Output file path (default: stdout)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    default="csv",
    help="Output format.",
)
@click.option(
    "--all-episodes / --played-episodes",
    "all_episodes",
    default=False,
    is_flag=True,
    show_default=True,
    help="Only played or all episodes from selected feeds",
)
@click.option(
    "-a",
    "--all-feeds / --subbed-feeds",
    "all_feeds",
    is_flag=True,
    default=False,
    show_default=True,
    help="Select from subscribed or all feeds.",
)
@click.option(
    "-c",
    "--count",
    type=int,
    help="Limit the number of episodes returned.",
)
def episodes(
    ctx: click.Context,
    db_path: str | None,
    feed_titles: tuple[str, ...],
    output_path: str | None,
    output_format: str,
    all_episodes: bool,
    all_feeds: bool,
    count: int | None,
) -> None:
    """Export episodes as CSV or JSON filtered by feed titles.

    If no feed titles are provided, exports episodes from all feeds.
    """

    resolved_db_path = _resolve_db_path(ctx, db_path)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(resolved_db_path)

    # If no feed titles provided, get all feed titles from the database
    titles_to_query = list(feed_titles)
    if not titles_to_query:
        titles_to_query = db.get_feed_titles(subscribed_only=not all_feeds)
        if titles_to_query:
            feed_type = "all" if not all_feeds else "all known"
            click.echo(
                f"No feed titles specified, using {feed_type} {len(titles_to_query)} feeds",
                err=True,
            )

    episodes_data = db.get_episodes_by_feed_titles(
        titles_to_query,
        all_episodes=all_episodes,
    )

    # Limit the number of episodes if count is specified
    if count is not None and count > 0:
        original_count = len(episodes_data)
        # Sort in descending order by userUpdatedDate before limiting
        episodes_data = sorted(
            episodes_data, key=lambda x: x.get("userUpdatedDate", ""), reverse=True
        )[:count]
        if original_count > count:
            click.echo(
                f"Limiting output to {count} episodes (from {original_count} total)",
                err=True,
            )

    if not episodes_data:
        if feed_titles:
            click.echo("No episodes found for the specified feed titles.", err=True)
        else:
            click.echo("No episodes found in the database.", err=True)
        return

    if output_path is None:
        output_file = sys.stdout
        try:
            if output_format == "csv":
                fieldnames = [
                    "episode_title",
                    "feed_title",
                    "played",
                    "progress",
                    "userUpdatedDate",
                    "userRecommendedDate",
                    "pubDate",
                    "episode_url",
                    "enclosureUrl",
                ]
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(episodes_data)
            elif output_format == "json":
                json.dump(episodes_data, output_file, indent=2)
        finally:
            pass  # Don't close stdout
    else:
        # Use Path for file handling with context manager
        with Path(output_path).open(
            "w",
            newline="" if output_format == "csv" else None,
        ) as output_file:
            if output_format == "csv":
                fieldnames = [
                    "episode_title",
                    "feed_title",
                    "played",
                    "progress",
                    "userUpdatedDate",
                    "userRecommendedDate",
                    "pubDate",
                    "episode_url",
                    "enclosureUrl",
                ]
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(episodes_data)
            elif output_format == "json":
                json.dump(episodes_data, output_file, indent=2)

        click.echo(
            f"📝Exported {len(episodes_data)} episodes to {output_path} as {output_format.upper()}",
        )


@overcast.command()
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option(
    "--all",
    "all_feeds",
    is_flag=True,
    help="List all feeds known to Overcast, not just subscribed ones.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output feed data in JSON format.",
)
def subscriptions(
    ctx: click.Context, db_path: str | None, all_feeds: bool, json_output: bool
) -> None:
    """List feed titles.

    Default is only podcasts subscribed in Overcast.

    Use --json to output detailed feed data in JSON format.
    """

    resolved_db_path = _resolve_db_path(ctx, db_path)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(resolved_db_path)

    if json_output:
        feed_data = db.get_feed_data(subscribed_only=not all_feeds)
        click.echo(json.dumps(feed_data, indent=2))
    else:
        feed_titles = db.get_feed_titles(subscribed_only=not all_feeds)
        for title in feed_titles:
            click.echo(title)


@overcast.command("all")
@click.pass_context
@click.option(
    "-d",
    "--database",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    help="Path to database file (defaults to retrocast.db in app directory)",
)
@click.option(
    "-a",
    "--auth",
    "custom_auth_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    help="Custom path to auth.json file (defaults to app directory)",
)
@click.option("-v", "--verbose", is_flag=True)
def save_extend_download(
    ctx: click.core.Context,
    db_path: str | None,
    custom_auth_path: str | None,
    verbose: bool,
) -> None:
    """Run all steps to save, extend, download transcripts, and chapters.

    This command sequentially executes the following:
    1. Save Overcast information to the SQLite database.
    2. Extend the database with new feed and episode data.
    3. Download available transcripts for all or starred episodes.
    4. Download and store available chapters for all or starred episodes.
    """

    resolved_db_path = _resolve_db_path(ctx, db_path)

    if not _confirm_db_creation(resolved_db_path):
        click.echo("Database creation cancelled.")
        return
    ctx.invoke(
        save,
        db_path=resolved_db_path,
        custom_auth_path=custom_auth_path,
        load=None,
        no_archive=False,
        verbose=verbose,
    )
    ctx.invoke(
        extend,
        db_path=resolved_db_path,
        no_archive=False,
        verbose=verbose,
    )
    ctx.invoke(
        transcripts,
        db_path=resolved_db_path,
        archive_path=None,
        starred_only=False,
        verbose=verbose,
    )
    ctx.invoke(
        chapters,
        db_path=resolved_db_path,
        archive_path=None,
    )
