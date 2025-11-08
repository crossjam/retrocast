#!/usr/bin/env python
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree

import click
from click_default_group import DefaultGroup
import requests

from retrocast.appdir import get_app_dir, get_auth_path, get_default_db_path
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
        f"Database file '{db_path}' does not exist. Create it?",
        default=True,
    )


@click.group(cls=DefaultGroup, default="about", default_if_no_args=True)
@click.version_option()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Save listening history and feed/episode info from Overcast to SQLite."""
    # Initialize context object if it doesn't exist
    ctx.ensure_object(dict)
    # Store app directory in context
    ctx.obj["app_dir"] = get_app_dir()


@cli.command()
def about() -> None:
    """Show information about Retrocast."""

    click.echo(
        "Retrocast saves your Overcast listening history and related metadata "
        "to a local SQLite database."
    )


@cli.command()
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
    auth_path = custom_auth_path if custom_auth_path else str(get_auth_path())
    click.echo("Logging in to Overcast")
    click.echo(
        f"Your password is not stored but an auth cookie will be saved to {auth_path}",
    )
    click.echo()
    auth_and_save_cookies(email, password, auth_path)


@cli.command()
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
    db_path: str,
    custom_auth_path: str | None,
    load: str | None,
    no_archive: bool,
    verbose: bool,
) -> None:
    """Save Overcast info to SQLite database."""

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

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
            custom_auth_path,
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


@cli.command()
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
    db_path: str,
    no_archive: bool,
    verbose: bool,
) -> None:
    """Download XML feed and extract all feed and episode tags and attributes."""

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

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
    db_path: str,
    archive_path: str | None,
    starred_only: bool,
    verbose: bool,
) -> None:
    """Download available transcripts for all or starred episodes."""

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)

    transcripts_path = Path(archive_path) if archive_path else _archive_path(db_path, "transcripts")

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
    db_path: str,
    archive_path: str | None,
) -> None:
    """Download and store available chapters for all or starred episodes."""

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    archive_root = Path(archive_path) if archive_path else app_dir / "archive"
    backfill_all_chapters(db_path, archive_root)


@cli.command()
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
    db_path: str,
    output_path: str | None,
) -> None:
    """Download and store available chapters for all or starred episodes."""

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    if output_path:
        if Path(output_path).is_dir():
            html_output_path = Path(output_path) / "overcast-played.html"
        else:
            html_output_path = Path(output_path)
    else:
        html_output_path = app_dir / "retrocast-played.html"
    generate_html_played(db_path, html_output_path)
    print(f"📝Saved HTML to: file://{html_output_path.absolute()}")


@cli.command()
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
    db_path: str,
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

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)

    # If no feed titles provided, get all feed titles from the database
    titles_to_query = list(feed_titles)
    if not titles_to_query:
        titles_to_query = db.get_feed_titles(subscribed_only=not all_feeds)
        if titles_to_query:
            feed_type = "all" if not all_feeds else "all known"
            click.echo(
                f"No feed titles specified, " f"using {feed_type} {len(titles_to_query)} feeds",
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
            f"📝Exported {len(episodes_data)} episodes to {output_path} "
            f"as {output_format.upper()}",
        )


@cli.command()
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
def subscriptions(ctx: click.Context, db_path: str, all_feeds: bool, json_output: bool) -> None:
    """List feed titles.

    Default is only podcasts subscribed in Overcast.

    Use --json to output detailed feed data in JSON format.
    """

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return

    db = Datastore(db_path)

    if json_output:
        feed_data = db.get_feed_data(subscribed_only=not all_feeds)
        click.echo(json.dumps(feed_data, indent=2))
    else:
        feed_titles = db.get_feed_titles(subscribed_only=not all_feeds)
        for title in feed_titles:
            click.echo(title)


@cli.command("all")
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
    db_path: str,
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

    app_dir = ctx.obj["app_dir"]

    # Use default db path if not specified
    if db_path is None:
        db_path = str(get_default_db_path())
    # If db_path is not absolute, make it relative to app_dir
    elif not Path(db_path).is_absolute():
        db_path = str(app_dir / db_path)

    if not _confirm_db_creation(db_path):
        click.echo("Database creation cancelled.")
        return
    ctx.invoke(
        save,
        db_path=db_path,
        custom_auth_path=custom_auth_path,
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
