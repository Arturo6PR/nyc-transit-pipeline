"""
MTA API client

Purpose:
- Fetch raw GTFS-Realtime bytes
- Handle authentication and feed URLs

TODO (Team):
- Parsing must NOT be added here
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote
import requests


@dataclass(frozen=True)
class FetchResult:
    feed_path: str
    url: str
    status_code: int
    payload_bytes: bytes
    error: Optional[str]


def build_feed_url(base_url: str, feed_path: str) -> str:
    """Part 1: Encode feed path"""
    encoded = quote(feed_path, safe="")
    return f"{base_url.rstrip('/')}/{encoded}"


def fetch_feed(base_url: str, api_key: str, feed_path: str, timeout_s: int = 20) -> FetchResult:
    """
    Part 2: Fetch feed bytes

    TODO (Team):
    - Save raw payload to DB
    - Parse payload downstream
    """
    url = build_feed_url(base_url, feed_path)

    try:
        resp = requests.get(url, headers={"x-api-key": api_key}, timeout=timeout_s)
        return FetchResult(
            feed_path=feed_path,
            url=url,
            status_code=resp.status_code,
            payload_bytes=resp.content,
            error=None if resp.status_code == 200 else resp.text[:300],
        )
    except Exception as exc:
        return FetchResult(
            feed_path=feed_path,
            url=url,
            status_code=0,
            payload_bytes=b"",
            error=str(exc),
        )