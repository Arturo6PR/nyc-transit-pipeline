from __future__ import annotations

import pytest
from google.transit import gtfs_realtime_pb2

from transitpulse.errors import FeedParseError
from transitpulse.parser import parse_feed


def test_parse_feed_normalizes_and_sorts_trip_events(feed_bytes: bytes) -> None:
    parsed = parse_feed(feed_bytes)

    assert parsed.feed_timestamp == 1_700_000_000
    assert parsed.incrementality == "FULL_DATASET"
    assert [
        (event.route_id, event.trip_id, event.stop_sequence, event.stop_id)
        for event in parsed.trip_stop_events
    ] == [
        ("A", "A-100", 1, "A01N"),
        ("A", "A-100", 2, "A02N"),
        ("B", "B-200", 1, "B03N"),
    ]
    assert parsed.trip_stop_events[0].arrival_delay == 120
    assert parsed.trip_stop_events[2].arrival_time is None
    assert parsed.trip_stop_events[2].departure_delay == 30


def test_parse_feed_normalizes_alerts(feed_bytes: bytes) -> None:
    alert = parse_feed(feed_bytes).alerts[0]

    assert alert.entity_id == "maintenance-1"
    assert alert.cause == "MAINTENANCE"
    assert alert.effect == "SIGNIFICANT_DELAYS"
    assert alert.header_text == "Maintenance delays"
    assert alert.description_text == "Expect longer waits on A and B service."
    assert alert.active_start == 1_700_000_100
    assert alert.active_end == 1_700_004_000
    assert alert.route_ids == ("A", "B")


def test_translation_falls_back_to_first_available() -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "alert"
    translation = entity.alert.header_text.translation.add()
    translation.language = "es"
    translation.text = "Servicio reducido"

    assert parse_feed(feed.SerializeToString()).alerts[0].header_text == "Servicio reducido"


def test_valid_empty_feed_returns_empty_records() -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"

    parsed = parse_feed(feed.SerializeToString())

    assert parsed.feed_timestamp is None
    assert parsed.trip_stop_events == ()
    assert parsed.alerts == ()


@pytest.mark.parametrize("payload", [b"", b"not-protobuf"])
def test_empty_or_malformed_feed_is_rejected(payload: bytes) -> None:
    with pytest.raises(FeedParseError):
        parse_feed(payload)
