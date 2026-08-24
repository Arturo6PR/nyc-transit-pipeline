from __future__ import annotations

import json

from transitpulse.render import render_json, render_text


def test_json_rendering_is_sorted_deterministic_and_parseable() -> None:
    report = {"operation": "summary", "report_schema_version": "1.1", "counts": {"z": 1}}

    first = render_json(report)
    second = render_json(report)

    assert first == second
    assert first.endswith("\n")
    assert first.index('"counts"') < first.index('"operation"')
    assert json.loads(first) == report


def test_text_ingestion_rendering_has_core_fields() -> None:
    report = {
        "operation": "ingest",
        "status": "INGESTED",
        "source": "fixture",
        "ingestion_id": "abc",
        "feed_timestamp": 123,
        "counts": {"trip_stop_events": 2, "alerts": 1},
    }

    text = render_text(report)

    assert text.startswith("TransitPulse ingestion\n")
    assert "Status: INGESTED" in text
    assert "Trip-stop events: 2" in text
