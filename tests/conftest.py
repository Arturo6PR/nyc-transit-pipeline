from __future__ import annotations

import base64
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from google.transit import gtfs_realtime_pb2


def build_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.incrementality = gtfs_realtime_pb2.FeedHeader.FULL_DATASET
    feed.header.timestamp = 1_700_000_000

    trip_b = feed.entity.add()
    trip_b.id = "trip-b-entity"
    trip_b.trip_update.trip.trip_id = "B-200"
    trip_b.trip_update.trip.route_id = "B"
    b_stop = trip_b.trip_update.stop_time_update.add()
    b_stop.stop_id = "B03N"
    b_stop.stop_sequence = 1
    b_stop.departure.time = 1_700_000_090
    b_stop.departure.delay = 30

    trip_a = feed.entity.add()
    trip_a.id = "trip-a-entity"
    trip_a.trip_update.trip.trip_id = "A-100"
    trip_a.trip_update.trip.route_id = "A"

    a_stop_two = trip_a.trip_update.stop_time_update.add()
    a_stop_two.stop_id = "A02N"
    a_stop_two.stop_sequence = 2
    a_stop_two.arrival.time = 1_700_000_600
    a_stop_two.arrival.delay = 600
    a_stop_two.departure.time = 1_700_000_630
    a_stop_two.departure.delay = 580

    a_stop_one = trip_a.trip_update.stop_time_update.add()
    a_stop_one.stop_id = "A01N"
    a_stop_one.stop_sequence = 1
    a_stop_one.arrival.time = 1_700_000_120
    a_stop_one.arrival.delay = 120
    a_stop_one.departure.time = 1_700_000_150
    a_stop_one.departure.delay = 110

    alert_entity = feed.entity.add()
    alert_entity.id = "maintenance-1"
    alert = alert_entity.alert
    alert.cause = gtfs_realtime_pb2.Alert.MAINTENANCE
    alert.effect = gtfs_realtime_pb2.Alert.SIGNIFICANT_DELAYS

    later = alert.active_period.add()
    later.start = 1_700_000_300
    later.end = 1_700_004_000
    earlier = alert.active_period.add()
    earlier.start = 1_700_000_100
    earlier.end = 1_700_003_000

    for route_id in ("B", "A", "A"):
        alert.informed_entity.add().route_id = route_id

    spanish = alert.header_text.translation.add()
    spanish.language = "es"
    spanish.text = "Retrasos por mantenimiento"
    english = alert.header_text.translation.add()
    english.language = "en-US"
    english.text = "Maintenance delays"
    description = alert.description_text.translation.add()
    description.language = "en"
    description.text = "Expect longer waits on A and B service."

    return feed.SerializeToString()


@pytest.fixture
def feed_bytes() -> bytes:
    return build_feed()


@pytest.fixture
def feed_file(tmp_path: Path, feed_bytes: bytes) -> Path:
    path = tmp_path / "feed sample.pb"
    path.write_bytes(feed_bytes)
    return path


@pytest.fixture
def base64_feed_file(tmp_path: Path, feed_bytes: bytes) -> Path:
    path = tmp_path / "feed sample.pb64"
    path.write_bytes(base64.b64encode(feed_bytes))
    return path


@pytest.fixture
def schedule_files() -> dict[str, bytes]:
    schedule_path = Path(__file__).parents[1] / "examples" / "gtfs_schedule"
    return {
        name: (schedule_path / name).read_bytes()
        for name in ("routes.txt", "trips.txt", "stops.txt", "stop_times.txt")
    }


@pytest.fixture
def schedule_dir(tmp_path: Path, schedule_files: dict[str, bytes]) -> Path:
    path = tmp_path / "schedule with spaces"
    path.mkdir()
    for name, data in schedule_files.items():
        (path / name).write_bytes(data)
    return path


@pytest.fixture
def schedule_zip(tmp_path: Path, schedule_files: dict[str, bytes]) -> Path:
    path = tmp_path / "schedule.zip"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, data in reversed(tuple(schedule_files.items())):
            archive.writestr(f"nested/{name}", data)
    return path
