import logging
import time

from src.config import get_settings
from src.db import get_engine, health_check
from src.mta_client import fetch_feed
from src.gtfs_parser import parse_gtfs_rt, parse_alerts
from src.db_writer import insert_raw_payload, insert_trip_updates, insert_alerts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def process_feed(engine, settings, feed_path: str) -> None:
    log.info(f"Fetching feed: {feed_path}")

    result = fetch_feed(
        settings.mta_base_url,
        settings.mta_api_key,
        feed_path,
    )

    try:
        insert_raw_payload(engine, result)
        log.info(f"{feed_path}: raw payload saved ({result.status_code})")
    except Exception as e:
        log.error(f"{feed_path}: failed to save raw payload — {e}")

    if result.status_code != 200:
        log.error(f"{feed_path}: bad status {result.status_code} — {result.error}")
        return

    try:
        trip_rows = parse_gtfs_rt(result.payload_bytes, feed_path)
        insert_trip_updates(engine, trip_rows)
        log.info(f"{feed_path}: inserted {len(trip_rows)} trip update rows")
    except Exception as e:
        log.error(f"{feed_path}: trip update pipeline failed — {e}")

    try:
        alert_rows = parse_alerts(result.payload_bytes, feed_path)
        insert_alerts(engine, alert_rows)
        log.info(f"{feed_path}: inserted {len(alert_rows)} alert rows")
    except Exception as e:
        log.error(f"{feed_path}: alert pipeline failed — {e}")


def main() -> None:
    log.info(" Ingestion cycle started ")
    settings = get_settings()
    engine = get_engine(settings.db_url)

    try:
        health_check(engine)
        log.info("DB health check passed")
    except Exception as e:
        log.error(f"DB health check failed — aborting: {e}")
        return

    for feed_path in settings.mta_feeds:
        try:
            process_feed(engine, settings, feed_path)
        except Exception as e:
            log.error(f"{feed_path}: unexpected error — {e}")

    log.info(" Ingestion cycle complete ")


def run_scheduler(interval_seconds: int = 3600) -> None:
    settings = get_settings()
    interval = settings.ingest_interval_seconds
    log.info(f"Scheduler started — running every {interval}s")
    while True:
        start = time.time()
        main()
        elapsed = time.time() - start
        sleep_for = max(0, interval - elapsed)
        log.info(f"Next run in {sleep_for:.0f}s")
        time.sleep(sleep_for)


if __name__ == "__main__":
    run_scheduler()