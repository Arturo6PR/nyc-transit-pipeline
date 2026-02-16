from sqlalchemy import text


def insert_trip_updates(engine, rows):
    if not rows:
        return

    query = text("""
        INSERT INTO trip_updates (
            fetched_at,
            feed_path,
            trip_id,
            route_id,
            stop_id,
            arrival_time,
            arrival_delay
        )
        VALUES (
            :timestamp,
            :feed_path,
            :trip_id,
            :route_id,
            :stop_id,
            :arrival_time,
            :delay
        )
    """)

    with engine.begin() as conn:
        conn.execute(query, rows)