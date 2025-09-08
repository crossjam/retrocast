#!/usr/bin/env python
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree

import click
import requests

from retrocast.chapters_backfill import backfill_all_chapters
from retrocast.html.page import generate_html_played

from .constants import BATCH_SIZE, TITLE
from .datastore import Datastore
from .feed import fetch_xml_and_extract
from .overcast import (
    _session_from_cookie,
    _session_from_json,
    auth_and_save_cookies,
    extract_feed_and_episodes_from_opml,
    extract_playlists_from_opml,
    fetch_opml,
)
from .utils import (
    _archive_path,
    _file_extension_for_type,
    _headers_ua,
    _sanitize_for_path,
)


def _confirm_db_creation(db_path: str) -> bool:
    """Confirm database creation if it doesn't exist."""
    if Datastore.exists(db_path):
        return True

    return click.confirm(
        f"Database file '{db_path}' does not exist. Create it?", default=True,
    )


@click.group()
@click.version_option()
def cli() -> None:
    """Save listening history and feed/episode info from Overcast to SQLite."""


@cli.command()
@click.option(
    "-a",
    "--auth",
    "auth_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save auth cookie, defaults to auth.json",
)
@click.option(
    "--email",
    prompt=True,
    hide_input=False,
)
@click.password_option()
def auth(auth_path: str, email: str, password: str) -> None:
    """Save authentication credentials to a JSON file."""
    click.echo("Logging in to Overcast")
    click.echo(
        f"Your password is not stored but an auth cookie will be saved to {auth_path}",
    )
    click.echo()
    auth_and_save_cookies(email, password, auth_path)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
)
@click.option(
    "-a",
    "--auth",
    "auth_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json file",
)
@click.option(
    "--load",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    help="Load OPML from this file instead of the API",
)
@click.option("-na", "--no-archive", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def save(
    db_path: str,
    auth_path: str,
    load: str | None,
    no_archive: bool,
    verbose: bool,
) -> None:
    """Save Overcast info to SQLite database."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)
    ingested_feed_ids = set()
    if load:
        xml = Path(load).read_text()
    else:
        print("🔉Fetching latest OPML from Overcast")
        xml = _auth_and_fetch(
            auth_path,
            None if no_archive else _archive_path(db_path, "retrocast"),
        )

    if verbose:
        print("📥Parsing OPML...")
    root = ElementTree.fromstring(xml)

    for playlist in extract_playlists_from_opml(root):
        if verbose:
            print(f"▶️Saving playlist: {playlist['title']}")
        db.save_playlist(playlist)

    for feed, episodes in extract_feed_and_episodes_from_opml(root):
        if not episodes:
            if verbose:
                print(f"⚠️Skipping {feed[TITLE]} (no episodes)")
            continue
        if verbose:
            print(f"⤵️Saving {feed[TITLE]} (latest: {episodes[0][TITLE]})")
        ingested_feed_ids.add(feed["overcastId"])
        db.save_feed_and_episodes(feed, episodes)

    db.mark_feed_removed_if_missing(ingested_feed_ids)


def _auth_and_fetch(auth_path: str, archive: Path | None) -> str:
    if (cookie := os.getenv("OVERCAST_COOKIE")) is not None:
        session = _session_from_cookie(cookie)
    else:
        if not Path(auth_path).exists():
            auth(auth_path)
        session = _session_from_json(auth_path)
    return fetch_opml(session, archive)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
)
@click.option("-na", "--no-archive", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def extend(
    db_path: str,
    no_archive: bool,
    verbose: bool,
) -> None:
    """Download XML feed and extract all feed and episode tags and attributes."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)
    feeds_to_extend = db.get_feeds_to_extend()
    print(f"➡️Extending {len(feeds_to_extend)} feeds")

    archive_dir = None if no_archive else _archive_path(db_path, "feeds")

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
                print(f"⚠️Skipping {title} (no episodes)")
        else:
            if verbose:
                print(f"⏩️Extending {title} (latest: {episodes[0][TITLE]})")
            if "errorCode" in feed:
                print(f"⛔️Found error: {feed['errorCode']}")
        return feed, episodes

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        results = list(executor.map(_fetch_feed_extend_save, feeds_to_extend))

    if verbose:
        print(f"Saving {len(results)} feeds to database")
    for feed, episodes in results:
        db.save_extended_feed_and_episodes(feed, episodes)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
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
    db_path: str,
    archive_path: str | None,
    starred_only: bool,
    verbose: bool,
) -> None:
    """Download available transcripts for all or starred episodes."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)

    transcripts_path = (
        Path(archive_path) if archive_path else _archive_path(db_path, "transcripts")
    )

    transcripts_path.mkdir(parents=True, exist_ok=True)

    if db.ensure_transcript_columns():
        print("⚠️No transcript URLs found in database, please run `extend`")

    transcripts_to_download = list(
        db.transcripts_to_download(starred_only=starred_only),
    )

    if verbose:
        print(f"🔉Downloading {len(transcripts_to_download)} transcripts...")

    def _fetch_and_write_transcript(
        transcript: tuple[str, str, str, str, str],
    ) -> tuple[str, str] | None:

        title, url, mimetype, enclosure, feed_title = transcript
        if verbose:
            print(f"⬇️Downloading {title} @ {url}")
        try:
            response = requests.get(url, headers=_headers_ua())
        except requests.exceptions.RequestException as e:
            print(f"⛔ Error downloading {url}: {e}")
            return None

        if not response.ok:
            print(f"⛔ Error code {response.status_code} downloading {url}")
            if verbose:
                print(response.headers)
            return None
        feed_path = transcripts_path / _sanitize_for_path(feed_title)
        feed_path.mkdir(exist_ok=True)
        file_ext = _file_extension_for_type(response.headers, mimetype)
        file_path = feed_path / (_sanitize_for_path(title) + file_ext)
        if verbose:
            print(f"📝Saving {file_path}")
        with file_path.open(mode="wb") as file:
            file.write(response.content)
        return enclosure, str(file_path.absolute())

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        results = list(
            executor.map(_fetch_and_write_transcript, transcripts_to_download),
        )

    if verbose:
        print(f"Saving {len(results)} transcripts to database")
    for row in results:
        if row is not None:
            enclosure, file_path = row
            db.update_transcript_download_paths(
                enclosure,
                str(file_path),
            )


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
)
@click.option(
    "-p",
    "--path",
    "archive_path",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
)
def chapters(
    db_path: str,
    archive_path: str | None,
) -> None:
    """Download and store available chapters for all or starred episodes."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    archive_root = (
        Path(archive_path) if archive_path else Path(db_path).parent / "archive"
    )
    backfill_all_chapters(db_path, archive_root)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
)
def html(
    db_path: str,
    output_path: str | None,
) -> None:
    """Download and store available chapters for all or starred episodes."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    if output_path:
        if Path(output_path).is_dir():
            html_output_path = Path(output_path) / "overcast-played.html"
        else:
            html_output_path = Path(output_path)
    else:
        html_output_path = Path(db_path).parent / "retrocast-played.html"
    generate_html_played(db_path, html_output_path)
    print(f"📝Saved HTML to: file://{html_output_path.absolute()}")


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
)
@click.argument("feed_titles", nargs=-1, required=True)
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
    "--all",
    "all_episodes",
    is_flag=True,
    help="Retrieve all matching episodes, not just played ones.",
)
def episodes(
    db_path: str,
    feed_titles: tuple[str, ...],
    output_path: str | None,
    output_format: str,
    all_episodes: bool,
) -> None:
    """Export episodes as CSV or JSON filtered by feed titles."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)
    episodes_data = db.get_episodes_by_feed_titles(
        list(feed_titles), all_episodes=all_episodes,
    )

    if not episodes_data:
        click.echo("No episodes found for the specified feed titles.", err=True)
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
            "w", newline="" if output_format == "csv" else None,
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
            f"📝Exported {len(episodes_data)} episodes to {output_path} "
            f"as {output_format.upper()}",
        )


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="retrocast.db",
)
@click.option(
    "--all",
    "all_feeds",
    is_flag=True,
    help="List all feeds, not just subscribed ones.",
)
def subscriptions(db_path: str, all_feeds: bool) -> None:
    """List feed titles."""
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)
    feed_titles = db.get_feed_titles(subscribed_only=not all_feeds)
    for title in feed_titles:
        click.echo(title)


@cli.command("all")
@click.pass_context
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="overcast.db",
)
@click.option(
    "-a",
    "--auth",
    "auth_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json file",
)
@click.option("-v", "--verbose", is_flag=True)
def save_extend_download(
    ctx: click.core.Context,
    db_path: str,
    auth_path: str,
    verbose: bool,
) -> None:
    """Run all steps to save, extend, download transcripts, and chapters.

    This command sequentially executes the following:
    1. Save Overcast information to the SQLite database.
    2. Extend the database with new feed and episode data.
    3. Download available transcripts for all or starred episodes.
    4. Download and store available chapters for all or starred episodes.
    """
    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return
    ctx.invoke(
        save,
        db_path=db_path,
        auth_path=auth_path,
        load=None,
        no_archive=False,
        verbose=verbose,
    )
    ctx.invoke(
        extend,
        db_path=db_path,
        no_archive=False,
        verbose=verbose,
    )
    ctx.invoke(
        transcripts,
        db_path=db_path,
        archive_path=None,
        starred_only=False,
        verbose=verbose,
    )
    ctx.invoke(
        chapters,
        db_path=db_path,
        archive_path=None,
    )


if __name__ == "__main__":
    cli()
