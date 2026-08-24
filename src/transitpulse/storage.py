"""Embedded DuckDB persistence and analytical summaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType

import duckdb

from transitpulse.errors import StorageError
from transitpulse.models import ParsedFeed

DATABASE_SCHEMA_VERSION = 1
DELAY_THRESHOLD_SECONDS = 300


class TransitStore:
    """Own the DuckDB schema and transaction boundary for one database."""

    def __init__(self, database: str | Path) -> None:
        value = str(database)
        if value != ":memory:":
            path = Path(value).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            value = str(path)
        try:
            self.connection = duckdb.connect(value)
            self._initialize()
        except (duckdb.Error, OSError) as exc:
            raise StorageError(f"could not open analytical store: {exc}") from exc

    def __enter__(self) -> TransitStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key VARCHAR PRIMARY KEY,
                value VARCHAR NOT NULL
            );
            INSERT OR IGNORE INTO metadata VALUES ('schema_version', '1');

            CREATE TABLE IF NOT EXISTS ingestion_runs (
                ingestion_id VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                payload_sha256 VARCHAR NOT NULL,
                feed_timestamp BIGINT,
                incrementality VARCHAR NOT NULL,
                trip_stop_event_count INTEGER NOT NULL,
                alert_count INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_payloads (
                ingestion_id VARCHAR PRIMARY KEY,
                payload BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trip_stop_events (
                event_id VARCHAR PRIMARY KEY,
                ingestion_id VARCHAR NOT NULL,
                entity_id VARCHAR NOT NULL,
                trip_id VARCHAR NOT NULL,
                route_id VARCHAR NOT NULL,
                stop_id VARCHAR NOT NULL,
                stop_sequence INTEGER,
                arrival_time BIGINT,
                arrival_delay INTEGER,
                departure_time BIGINT,
                departure_delay INTEGER
            );

            CREATE TABLE IF NOT EXISTS alerts (
                alert_id VARCHAR PRIMARY KEY,
                ingestion_id VARCHAR NOT NULL,
                entity_id VARCHAR NOT NULL,
                cause VARCHAR NOT NULL,
                effect VARCHAR NOT NULL,
                header_text VARCHAR,
                description_text VARCHAR,
                active_start BIGINT,
                active_end BIGINT,
                route_ids_json VARCHAR NOT NULL
            );
            """
        )

    def has_ingestion(self, ingestion_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM ingestion_runs WHERE ingestion_id = ?", [ingestion_id]
        ).fetchone()
        return row is not None

    def ingest(
        self,
        *,
        ingestion_id: str,
        source: str,
        payload_sha256: str,
        payload: bytes,
        feed: ParsedFeed,
        event_ids: tuple[str, ...],
        alert_ids: tuple[str, ...],
    ) -> bool:
        """Persist a feed atomically; return False when it was already ingested."""
        if self.has_ingestion(ingestion_id):
            return False

        try:
            self.connection.execute("BEGIN TRANSACTION")
            self.connection.execute(
                """
                INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ingestion_id,
                    source,
                    payload_sha256,
                    feed.feed_timestamp,
                    feed.incrementality,
                    len(feed.trip_stop_events),
                    len(feed.alerts),
                ],
            )
            self.connection.execute(
                "INSERT INTO raw_payloads VALUES (?, ?)", [ingestion_id, payload]
            )

            for event_id, event in zip(event_ids, feed.trip_stop_events, strict=True):
                self.connection.execute(
                    """
                    INSERT INTO trip_stop_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        event_id,
                        ingestion_id,
                        event.entity_id,
                        event.trip_id,
                        event.route_id,
                        event.stop_id,
                        event.stop_sequence,
                        event.arrival_time,
                        event.arrival_delay,
                        event.departure_time,
                        event.departure_delay,
                    ],
                )

            for alert_id, alert in zip(alert_ids, feed.alerts, strict=True):
                self.connection.execute(
                    """
                    INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        alert_id,
                        ingestion_id,
                        alert.entity_id,
                        alert.cause,
                        alert.effect,
                        alert.header_text,
                        alert.description_text,
                        alert.active_start,
                        alert.active_end,
                        json.dumps(alert.route_ids, separators=(",", ":")),
                    ],
                )
            self.connection.execute("COMMIT")
        except duckdb.Error as exc:
            self.connection.execute("ROLLBACK")
            raise StorageError(f"could not persist feed: {exc}") from exc
        return True

    def summary(self) -> dict[str, object]:
        counts = self.connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM ingestion_runs),
                (SELECT COUNT(*) FROM trip_stop_events),
                (SELECT COUNT(*) FROM alerts)
            """
        ).fetchone()
        assert counts is not None

        route_rows = self.connection.execute(
            """
            SELECT
                route_id,
                COUNT(*) AS event_count,
                ROUND(AVG(COALESCE(arrival_delay, departure_delay)), 2) AS average_delay_seconds,
                SUM(
                    CASE
                        WHEN COALESCE(arrival_delay, departure_delay) >= ? THEN 1
                        ELSE 0
                    END
                ) AS delayed_event_count
            FROM trip_stop_events
            GROUP BY route_id
            ORDER BY route_id
            """,
            [DELAY_THRESHOLD_SECONDS],
        ).fetchall()

        effect_rows = self.connection.execute(
            """
            SELECT effect, COUNT(*) AS alert_count
            FROM alerts
            GROUP BY effect
            ORDER BY effect
            """
        ).fetchall()

        return {
            "database_schema_version": DATABASE_SCHEMA_VERSION,
            "counts": {
                "ingestions": int(counts[0]),
                "trip_stop_events": int(counts[1]),
                "alerts": int(counts[2]),
            },
            "delay_threshold_seconds": DELAY_THRESHOLD_SECONDS,
            "routes": [
                {
                    "route_id": str(row[0]),
                    "event_count": int(row[1]),
                    "average_delay_seconds": float(row[2]) if row[2] is not None else None,
                    "delayed_event_count": int(row[3]),
                }
                for row in route_rows
            ],
            "alert_effects": [
                {"effect": str(row[0]), "alert_count": int(row[1])} for row in effect_rows
            ],
        }
