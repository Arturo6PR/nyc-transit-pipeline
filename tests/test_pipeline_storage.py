from __future__ import annotations

from pathlib import Path

from transitpulse.pipeline import ingest_feed, summarize


def test_first_ingestion_and_duplicate_are_idempotent(feed_file: Path, tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"

    first = ingest_feed(str(feed_file), database=database, source_label="mta-test")
    duplicate = ingest_feed(str(feed_file), database=database, source_label="mta-test")
    summary = summarize(database)

    assert first["status"] == "INGESTED"
    assert duplicate["status"] == "DUPLICATE"
    assert duplicate["ingestion_id"] == first["ingestion_id"]
    assert summary["counts"] == {
        "ingestions": 1,
        "trip_stop_events": 3,
        "alerts": 1,
    }


def test_same_feed_and_source_have_deterministic_identity(feed_file: Path, tmp_path: Path) -> None:
    one = ingest_feed(str(feed_file), database=tmp_path / "one.duckdb", source_label="mta-test")
    two = ingest_feed(str(feed_file), database=tmp_path / "two.duckdb", source_label="mta-test")

    assert one == two


def test_source_label_participates_in_identity(feed_file: Path, tmp_path: Path) -> None:
    database = tmp_path / "sources.duckdb"

    one = ingest_feed(str(feed_file), database=database, source_label="feed-one")
    two = ingest_feed(str(feed_file), database=database, source_label="feed-two")

    assert one["ingestion_id"] != two["ingestion_id"]
    assert summarize(database)["counts"]["ingestions"] == 2  # type: ignore[index]


def test_summary_is_ordered_and_calculates_route_metrics(feed_file: Path, tmp_path: Path) -> None:
    database = tmp_path / "summary.duckdb"
    ingest_feed(str(feed_file), database=database, source_label="mta-test")

    report = summarize(database)

    assert report["database_schema_version"] == 1
    assert report["delay_threshold_seconds"] == 300
    assert report["routes"] == [
        {
            "route_id": "A",
            "event_count": 2,
            "average_delay_seconds": 360.0,
            "delayed_event_count": 1,
        },
        {
            "route_id": "B",
            "event_count": 1,
            "average_delay_seconds": 30.0,
            "delayed_event_count": 0,
        },
    ]
    assert report["alert_effects"] == [{"effect": "SIGNIFICANT_DELAYS", "alert_count": 1}]


def test_empty_store_has_a_stable_summary(tmp_path: Path) -> None:
    report = summarize(tmp_path / "nested" / "empty.duckdb")

    assert report["counts"] == {
        "ingestions": 0,
        "trip_stop_events": 0,
        "alerts": 0,
    }
    assert report["routes"] == []
    assert report["alert_effects"] == []
