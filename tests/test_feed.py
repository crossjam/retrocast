from datetime import datetime

import pytest
import requests

import retrocast.feed as feed
from retrocast.constants import DESCRIPTION, ENCLOSURE_URL, FEED_XML_URL, TITLE, XML_URL
from retrocast.feed import fetch_xml_and_extract


@pytest.fixture()
def fixed_datetime(monkeypatch: pytest.MonkeyPatch) -> None:
    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2024, 1, 2, 12, 0, tzinfo=tz)

    monkeypatch.setattr(feed, "datetime", Fixed)


def test_fetch_xml_and_extract_success(requests_mock, fixed_datetime: None) -> None:
    xml_url = "https://example.test/feed.xml"
    xml_body = """<?xml version='1.0' encoding='UTF-8'?>
    <rss><channel>
      <title> Sample Feed </title>
      <description> Example description </description>
      <item>
        <title>Episode 1</title>
        <description>First episode</description>
        <enclosure url="https://cdn.example.test/ep1.mp3" length="123" type="audio/mpeg" />
      </item>
    </channel></rss>
    """
    requests_mock.get(xml_url, text=xml_body)

    feed_attrs, episodes, chapters = fetch_xml_and_extract(
        xml_url,
        "Sample Feed",
        None,
        verbose=False,
        headers={},
    )

    assert feed_attrs[XML_URL] == xml_url
    assert feed_attrs[TITLE] == "Sample Feed"
    assert feed_attrs[DESCRIPTION] == "Example description"
    assert feed_attrs["lastUpdated"] == "2024-01-02T12:00:00+00:00"
    assert chapters == []

    assert len(episodes) == 1
    assert episodes[0][FEED_XML_URL] == xml_url
    assert episodes[0][TITLE] == "Episode 1"
    assert episodes[0][DESCRIPTION] == "First episode"
    assert episodes[0][ENCLOSURE_URL] == "https://cdn.example.test/ep1.mp3"


def test_fetch_xml_and_extract_handles_non_ok_response(requests_mock, fixed_datetime: None) -> None:
    xml_url = "https://example.test/feed.xml"
    requests_mock.get(xml_url, status_code=502, text="bad gateway")

    feed_attrs, episodes, chapters = fetch_xml_and_extract(
        xml_url,
        "Sample Feed",
        None,
        verbose=False,
        headers={},
    )

    assert feed_attrs[XML_URL] == xml_url
    assert feed_attrs["errorCode"] == 502
    assert feed_attrs["lastUpdated"] == "2024-01-02T12:00:00+00:00"
    assert episodes == []
    assert chapters == []


def test_fetch_xml_and_extract_handles_request_exception(
    monkeypatch: pytest.MonkeyPatch, fixed_datetime: None
) -> None:
    xml_url = "https://example.test/feed.xml"

    def blow_up(*_, **__):
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr(feed, "_get_xml_with_retries", blow_up)

    feed_attrs, episodes, chapters = fetch_xml_and_extract(
        xml_url,
        "Sample Feed",
        None,
        verbose=False,
        headers={},
    )

    assert feed_attrs[XML_URL] == xml_url
    assert feed_attrs["errorCode"] == -1
    assert "timed out" in feed_attrs["errorMessage"]
    assert feed_attrs["lastUpdated"] == "2024-01-02T12:00:00+00:00"
    assert episodes == []
    assert chapters == []
