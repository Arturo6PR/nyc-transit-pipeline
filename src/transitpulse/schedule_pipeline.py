"""Application service for deterministic GTFS Schedule ingestion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from transitpulse.constants import REPORT_SCHEMA_VERSION
from transitpulse.schedule_parser import parse_schedule
from transitpulse.schedule_sources import load_schedule
from transitpulse.storage import TransitStore


def _canonical_schedule(schedule: object) -> bytes:
    return json.dumps(
        asdict(schedule),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def ingest_schedule(
    location: str,
    *,
    database: str | Path,
    source_label: str | None = None,
) -> dict[str, object]:
    loaded = load_schedule(location, source_label=source_label)
    schedule = parse_schedule(loaded.files)
    content_sha256 = hashlib.sha256(_canonical_schedule(schedule)).hexdigest()
    schedule_id = hashlib.sha256(f"{loaded.source_label}\0{content_sha256}".encode()).hexdigest()[
        :24
    ]

    with TransitStore(database) as store:
        inserted = store.ingest_schedule(
            schedule_id=schedule_id,
            source=loaded.source_label,
            content_sha256=content_sha256,
            input_format=loaded.input_format,
            raw_payload=loaded.raw_payload,
            schedule=schedule,
        )

    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "operation": "schedule_ingest",
        "status": "IMPORTED" if inserted else "DUPLICATE",
        "schedule_id": schedule_id,
        "source": loaded.source_label,
        "content_sha256": content_sha256,
        "input_format": loaded.input_format,
        "counts": {
            "routes": len(schedule.routes),
            "trips": len(schedule.trips),
            "stops": len(schedule.stops),
            "stop_times": len(schedule.stop_times),
        },
    }
