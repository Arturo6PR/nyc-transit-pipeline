from datetime import datetime
from sqlalchemy import text
from src.mta_client import FetchResult


def insert_raw_payload(engine, result: FetchResult) -> None:
    query = text("""
        INSERT INTO gtfs_rt_raw (
            feed_path,
            fetched_at,
            http_status,
            payload,
            payload_size_bytes,
            error
        )
        VALUES (
            :feed_path,
            :fetched_at,
            :http_status,
            :payload,
            :payload_size_bytes,
            :error
        )
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "feed_path": result.feed_path,
            "fetched_at": datetime.utcnow(),
            "http_status": result.status_code,
            "payload": result.payload_bytes,
            "payload_size_bytes": len(result.payload_bytes),
            "error": result.error,
        })


def insert_trip_updates(engine, rows: list[dict]) -> None:
    if not rows:
        return
    query = text("""
        INSERT INTO trip_updates (
            fetched_at,
            feed_path,
            trip_id,
            route_id,
            stop_id,
            stop_sequence,
            arrival_time,
            arrival_delay,
            departure_time,
            departure_delay
        )
        VALUES (
            :fetched_at,
            :feed_path,
            :trip_id,
            :route_id,
            :stop_id,
            :stop_sequence,
            :arrival_time,
            :arrival_delay,
            :departure_time,
            :departure_delay
        )
        ON CONFLICT DO NOTHING
    """)
    with engine.begin() as conn:
        conn.execute(query, rows)


def insert_alerts(engine, rows: list[dict]) -> None:
    if not rows:
        return
    query = text("""
        INSERT INTO alerts (
            fetched_at,
            feed_path,
            alert_id,
            cause,
            effect,
            header_text,
            description_text
        )
        VALUES (
            :fetched_at,
            :feed_path,
            :alert_id,
            :cause,
            :effect,
            :header_text,
            :description_text
        )
        ON CONFLICT DO NOTHING
    """)
    with engine.begin() as conn:
        conn.execute(query, rows)