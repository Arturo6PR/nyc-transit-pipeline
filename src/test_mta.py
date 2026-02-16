"""
MTA API test

Purpose:
- Validate API key
- Confirm feeds return data

TODO (Team):
- Parsing should NOT be done here
"""

from src.config import get_settings
from src.mta_client import fetch_feed


def main() -> None:
    settings = get_settings()

    if not settings.mta_api_key:
        raise ValueError("Missing MTA_API_KEY")

    for feed_path in settings.mta_feeds:
        result = fetch_feed(settings.mta_base_url, settings.mta_api_key, feed_path)
        print(feed_path, result.status_code, len(result.payload_bytes))


if __name__ == "__main__":
    main()