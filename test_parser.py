import pytest
from google.transit import gtfs_realtime_pb2
from datetime import datetime
from src.gtfs_parser import parse_gtfs_rt, parse_alerts


def make_trip_update_feed(
    trip_id="TRIP1",
    route_id="A",
    stop_id="STOP1",
    stop_sequence=3,
    arrival_time=1700000000,
    arrival_delay=120,
    departure_time=1700000060,
    departure_delay=90,
) -> bytes:
    """Build a minimal GTFS-RT feed with one trip update."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000

    entity = feed.entity.add()
    entity.id = "entity-1"

    tu = entity.trip_update
    tu.trip.trip_id = trip_id
    tu.trip.route_id = route_id

    stu = tu.stop_time_update.add()
    stu.stop_id = stop_id
    stu.stop_sequence = stop_sequence
    stu.arrival.time = arrival_time
    stu.arrival.delay = arrival_delay
    stu.departure.time = departure_time
    stu.departure.delay = departure_delay

    return feed.SerializeToString()


def make_alert_feed(
    alert_id="ALERT1",
    cause=gtfs_realtime_pb2.Alert.Cause.Value("MAINTENANCE"),
    effect=gtfs_realtime_pb2.Alert.Effect.Value("SIGNIFICANT_DELAYS"),
    header_en="Service suspended",
    description_en="No trains running",
) -> bytes:
    """Build a minimal GTFS-RT feed with one alert."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000

    entity = feed.entity.add()
    entity.id = alert_id

    alert = entity.alert
    alert.cause = cause
    alert.effect = effect

    t = alert.header_text.translation.add()
    t.text = header_en
    t.language = "en"

    t2 = alert.description_text.translation.add()
    t2.text = description_en
    t2.language = "en"

    return feed.SerializeToString()


# --- Trip update tests ---

def test_parse_gtfs_rt_returns_rows():
    payload = make_trip_update_feed()
    rows = parse_gtfs_rt(payload, "nyct/gtfs-ace")
    assert len(rows) == 1


def test_parse_gtfs_rt_fields():
    payload = make_trip_update_feed()
    row = parse_gtfs_rt(payload, "nyct/gtfs-ace")[0]

    assert row["trip_id"] == "TRIP1"
    assert row["route_id"] == "A"
    assert row["stop_id"] == "STOP1"
    assert row["stop_sequence"] == 3
    assert row["arrival_time"] == 1700000000
    assert row["arrival_delay"] == 120
    assert row["departure_time"] == 1700000060
    assert row["departure_delay"] == 90
    assert row["feed_path"] == "nyct/gtfs-ace"
    assert isinstance(row["fetched_at"], datetime)


def test_parse_gtfs_rt_empty_feed():
    # Empty feed should return no rows, not crash
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000
    rows = parse_gtfs_rt(feed.SerializeToString(), "nyct/gtfs-ace")
    assert rows == []


def test_parse_gtfs_rt_no_arrival():
    # Stop time update with no arrival field — should not crash
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000

    entity = feed.entity.add()
    entity.id = "e1"
    tu = entity.trip_update
    tu.trip.trip_id = "T1"
    tu.trip.route_id = "B"
    stu = tu.stop_time_update.add()
    stu.stop_id = "S1"
    stu.stop_sequence = 1

    rows = parse_gtfs_rt(feed.SerializeToString(), "nyct/gtfs-ace")
    assert len(rows) == 1
    assert rows[0]["arrival_time"] is None
    assert rows[0]["arrival_delay"] is None


# --- Alert tests ---

def test_parse_alerts_returns_rows():
    payload = make_alert_feed()
    rows = parse_alerts(payload, "nyct/gtfs-ace")
    assert len(rows) == 1


def test_parse_alerts_fields():
    payload = make_alert_feed()
    row = parse_alerts(payload, "nyct/gtfs-ace")[0]

    assert row["alert_id"] == "ALERT1"
    assert row["cause"] == "MAINTENANCE"
    assert row["effect"] == "SIGNIFICANT_DELAYS"
    assert row["header_text"] == "Service suspended"
    assert row["description_text"] == "No trains running"
    assert row["feed_path"] == "nyct/gtfs-ace"
    assert isinstance(row["fetched_at"], datetime)


def test_parse_alerts_empty_feed():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000
    rows = parse_alerts(feed.SerializeToString(), "nyct/gtfs-ace")
    assert rows == []


def test_parse_alerts_english_fallback():
    # Feed with only Spanish translation — should fall back to index 0
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000

    entity = feed.entity.add()
    entity.id = "A2"
    alert = entity.alert
    alert.cause = gtfs_realtime_pb2.Alert.Cause.Value("ACCIDENT")
    alert.effect = gtfs_realtime_pb2.Alert.Effect.Value("REDUCED_SERVICE")

    t = alert.header_text.translation.add()
    t.text = "Servicio reducido"
    t.language = "es"

    rows = parse_alerts(feed.SerializeToString(), "nyct/gtfs-ace")
    assert rows[0]["header_text"] == "Servicio reducido"