"""Application service connecting input, parsing, storage, and reports."""

from __future__ import annotations

import hashlib
from pathlib import Path

from transitpulse.parser import parse_feed
from transitpulse.sources import load_payload
from transitpulse.storage import TransitStore

REPORT_SCHEMA_VERSION = "1.0"


def _digest(*parts: str) -> str:
    value = "\0".join(parts).encode()
    return hashlib.sha256(value).hexdigest()


def ingest_feed(
    location: str,
    *,
    database: str | Path,
    source_label: str | None = None,
    timeout: float = 20,
) -> dict[str, object]:
    loaded = load_payload(location, source_label=source_label, timeout=timeout)
    payload_sha256 = hashlib.sha256(loaded.data).hexdigest()
    ingestion_id = _digest(loaded.source_label, payload_sha256)[:24]
    feed = parse_feed(loaded.data)

    event_ids = tuple(
        _digest(
            ingestion_id,
            event.entity_id,
            event.trip_id,
            event.stop_id,
            str(event.stop_sequence),
        )[:24]
        for event in feed.trip_stop_events
    )
    alert_ids = tuple(_digest(ingestion_id, alert.entity_id)[:24] for alert in feed.alerts)

    with TransitStore(database) as store:
        inserted = store.ingest(
            ingestion_id=ingestion_id,
            source=loaded.source_label,
            payload_sha256=payload_sha256,
            payload=loaded.data,
            feed=feed,
            event_ids=event_ids,
            alert_ids=alert_ids,
        )

    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "operation": "ingest",
        "status": "INGESTED" if inserted else "DUPLICATE",
        "ingestion_id": ingestion_id,
        "source": loaded.source_label,
        "payload_sha256": payload_sha256,
        "feed_timestamp": feed.feed_timestamp,
        "incrementality": feed.incrementality,
        "counts": {
            "trip_stop_events": len(feed.trip_stop_events),
            "alerts": len(feed.alerts),
        },
    }


def summarize(database: str | Path) -> dict[str, object]:
    with TransitStore(database) as store:
        details = store.summary()
    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "operation": "summary",
        **details,
    }
