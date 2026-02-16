from src.config import get_settings
from src.db import get_engine
from src.mta_client import fetch_feed
from src.gtfs_parser import parse_gtfs_rt
from src.db_writer import insert_trip_updates


def main():
    settings = get_settings()
    engine = get_engine(settings.db_url)

    for feed_path in settings.mta_feeds:
        response = fetch_feed(
            settings.mta_base_url,
            settings.mta_api_key,
            feed_path,
        )

        rows = parse_gtfs_rt(response.payload_bytes, feed_path)
        insert_trip_updates(engine, rows)

        print(f"{feed_path}: inserted {len(rows)} rows")


if __name__ == "__main__":
    main()