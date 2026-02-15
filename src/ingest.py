"""
Main ingestion pipeline

Purpose:
- Fetch GTFS-RT feeds
- Store raw payloads
- Parse payloads
- Store structured data

TODO (Team):
- Connect mta_client, gtfs_parser, and db_writer
"""

from src.config import get_settings
from src.db import get_engine
from src.mta_client import fetch_feed


def main() -> None:
    settings = get_settings()
    engine = get_engine(settings.db_url)

    for feed_path in settings.mta_feeds:
        result = fetch_feed(settings.mta_base_url, settings.mta_api_key, feed_path)
        print(feed_path, result.status_code)


if __name__ == "__main__":
    main()