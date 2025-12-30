from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import requests
import stamina
from podcast_chapter_tools.entities import Chapter

from .constants import (
    DESCRIPTION,
    TITLE,
    XML_URL,
)
from .episode import _element_to_dict, extract_ep_attrs
from .exceptions import NoChannelInFeedError


def fetch_xml_and_extract(
    xml_url: str,
    title: str,
    archive_dir: Path | None,
    *,
    verbose: bool,
    headers: dict,
) -> tuple[dict, list[dict], list[Chapter]]:
    """Fetch XML feed and extract all feed and episode tags and attributes."""
    now = datetime.now(tz=UTC).isoformat()
    try:
        response = _get_xml_with_retries(xml_url, headers)
    except requests.RequestException as exc:
        print(f"⛔️ Error fetching podcast feed {xml_url}: {exc}")
        return (
            {
                XML_URL: xml_url,
                "lastUpdated": now,
                "errorCode": -1,
                "errorMessage": str(exc),
            },
            [],
            [],
        )
    if not response.ok:
        print(f"⛔️ Error {response.status_code} fetching podcast feed {xml_url}")
        if verbose:
            print(response.headers)
        return (
            {
                XML_URL: xml_url,
                "lastUpdated": now,
                "errorCode": response.status_code,
            },
            [],
            [],
        )

    xml_string = response.text
    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_dir.joinpath(f"{title}.xml").write_text(xml_string)
        if verbose:
            print(f"Saving feed XML to {archive_dir}/{title}.xml")
    try:
        root = ElementTree.fromstring(xml_string)
    except ElementTree.ParseError:
        print(f"Failed to parse podcast feed {xml_url}.\n{response.headers}")
        return (
            {
                XML_URL: xml_url,
                "lastUpdated": now,
                "errorCode": -1,
            },
            [],
            [],
        )

    if (channel := root.find("./channel")) is None:
        raise NoChannelInFeedError

    return _extract_from_feed_xml(channel, now, xml_url)


def _extract_from_feed_xml(
    channel: ElementTree.Element,
    now: str,
    xml_url: str,
) -> tuple[dict, list[dict], list[Chapter]]:
    feed_attrs = {XML_URL: xml_url, "lastUpdated": now}
    episodes = []
    all_chapters = []
    for element in channel:
        if element.tag == "item":
            if (ep_info := extract_ep_attrs(xml_url, element)) is not None:
                ep_attrs, ep_chapters = ep_info
                episodes.append(ep_attrs)
                all_chapters.extend(ep_chapters)
        else:
            feed_attrs.update(_element_to_dict(element))
    feed_attrs[TITLE] = feed_attrs.get(TITLE, "").strip()
    feed_attrs[DESCRIPTION] = feed_attrs.get(DESCRIPTION, "").strip()

    return feed_attrs, episodes, all_chapters


@stamina.retry(
    on=(requests.RequestException,),
    attempts=4,
    wait_initial=0.5,
    wait_max=3.0,
)
def _get_xml_with_retries(xml_url: str, headers: dict) -> requests.Response:
    return requests.get(xml_url, headers=headers, timeout=10)
