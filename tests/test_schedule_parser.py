from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from transitpulse.errors import FeedParseError, InputLoadError
from transitpulse.schedule_parser import parse_schedule
from transitpulse.schedule_sources import load_schedule


def test_schedule_parser_normalizes_and_sorts(schedule_files: dict[str, bytes]) -> None:
    schedule = parse_schedule(schedule_files)

    assert [route.route_id for route in schedule.routes] == ["A", "B"]
    assert [trip.trip_id for trip in schedule.trips] == ["A-100", "B-200"]
    assert [stop.stop_id for stop in schedule.stops] == ["A01N", "A02N", "B03N", "B04N"]
    assert [(item.trip_id, item.stop_sequence) for item in schedule.stop_times] == [
        ("A-100", 1),
        ("A-100", 2),
        ("B-200", 1),
        ("B-200", 2),
    ]
    assert schedule.stop_times[2].arrival_seconds == 25 * 3600


def test_directory_and_zip_load_the_same_required_files(
    schedule_dir: Path, schedule_zip: Path
) -> None:
    directory = load_schedule(str(schedule_dir), source_label="mta-sample")
    archive = load_schedule(str(schedule_zip), source_label="mta-sample")

    assert directory.files == archive.files
    assert directory.input_format == "directory"
    assert archive.input_format == "zip"
    assert directory.raw_payload != archive.raw_payload


def test_missing_required_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InputLoadError, match=r"missing routes\.txt"):
        load_schedule(str(tmp_path))


def test_schedule_input_must_be_directory_or_zip(tmp_path: Path) -> None:
    path = tmp_path / "schedule.csv"
    path.write_text("data", encoding="utf-8")

    with pytest.raises(InputLoadError, match=r"directory or \.zip"):
        load_schedule(str(path))


def test_duplicate_route_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["routes.txt"] += b"MTA,A,A2,Duplicate route,1\n"

    with pytest.raises(FeedParseError, match="duplicate route_id"):
        parse_schedule(schedule_files)


def test_unknown_trip_route_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["trips.txt"] = schedule_files["trips.txt"].replace(
        b"A,WEEKDAY,A-100", b"Z,WEEKDAY,A-100"
    )

    with pytest.raises(FeedParseError, match="unknown route_id"):
        parse_schedule(schedule_files)


@pytest.mark.parametrize("bad_time", [b"08:61:00", b"eight", b"-1:00:00"])
def test_invalid_schedule_time_is_rejected(
    schedule_files: dict[str, bytes], bad_time: bytes
) -> None:
    schedule_files["stop_times.txt"] = schedule_files["stop_times.txt"].replace(
        b"08:00:00", bad_time
    )

    with pytest.raises(FeedParseError, match="invalid arrival_time"):
        parse_schedule(schedule_files)


def test_unknown_stop_reference_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["stop_times.txt"] = schedule_files["stop_times.txt"].replace(
        b"A01N,1", b"UNKNOWN,1"
    )

    with pytest.raises(FeedParseError, match="unknown stop_id"):
        parse_schedule(schedule_files)


def test_missing_required_column_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["routes.txt"] = schedule_files["routes.txt"].replace(
        b"route_type", b"vehicle_type"
    )

    with pytest.raises(FeedParseError, match="missing fields: route_type"):
        parse_schedule(schedule_files)


@pytest.mark.parametrize(
    ("filename", "extra_row", "message"),
    [
        ("trips.txt", b"A,WEEKDAY,A-100,Duplicate,0\n", "duplicate trip_id"),
        (
            "stop_times.txt",
            b"A-100,08:01:00,08:01:30,A01N,1\n",
            "duplicate trip_id/stop_sequence",
        ),
    ],
)
def test_duplicate_schedule_keys_are_rejected(
    schedule_files: dict[str, bytes], filename: str, extra_row: bytes, message: str
) -> None:
    schedule_files[filename] += extra_row

    with pytest.raises(FeedParseError, match=message):
        parse_schedule(schedule_files)


def test_invalid_coordinate_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["stops.txt"] = schedule_files["stops.txt"].replace(
        b"40.868072,-73.919899", b"91,-73.919899"
    )

    with pytest.raises(FeedParseError, match="out-of-range stop_lat"):
        parse_schedule(schedule_files)


def test_invalid_direction_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["trips.txt"] = schedule_files["trips.txt"].replace(
        b"Uptown and The Bronx,0", b"Uptown and The Bronx,2", 1
    )

    with pytest.raises(FeedParseError, match="invalid direction_id"):
        parse_schedule(schedule_files)


def test_unknown_parent_station_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["stops.txt"] += b"CHILD,Child stop,40,-73,UNKNOWN\n"

    with pytest.raises(FeedParseError, match="unknown parent_station"):
        parse_schedule(schedule_files)


@pytest.mark.parametrize(
    "replacement",
    [
        b"A-100,08:00:30,08:00:00,A01N,1",
        b"A-100,07:59:00,07:59:30,A02N,2",
    ],
)
def test_schedule_times_cannot_move_backwards(
    schedule_files: dict[str, bytes], replacement: bytes
) -> None:
    original = (
        b"A-100,08:00:00,08:00:30,A01N,1"
        if b"A01N" in replacement
        else b"A-100,08:05:00,08:05:30,A02N,2"
    )
    schedule_files["stop_times.txt"] = schedule_files["stop_times.txt"].replace(
        original, replacement
    )

    with pytest.raises(FeedParseError, match=r"departs before|decreasing times"):
        parse_schedule(schedule_files)


def test_header_only_file_is_rejected(schedule_files: dict[str, bytes]) -> None:
    schedule_files["routes.txt"] = (
        b"agency_id,route_id,route_short_name,route_long_name,route_type\n"
    )

    with pytest.raises(FeedParseError, match="contains no data rows"):
        parse_schedule(schedule_files)


def test_invalid_and_duplicate_zip_members_are_rejected(
    schedule_files: dict[str, bytes], tmp_path: Path
) -> None:
    invalid = tmp_path / "invalid.zip"
    invalid.write_bytes(b"not-a-zip")
    with pytest.raises(InputLoadError, match="invalid GTFS Schedule ZIP"):
        load_schedule(str(invalid))

    duplicate = tmp_path / "duplicate.zip"
    with ZipFile(duplicate, "w", ZIP_DEFLATED) as archive:
        for name, data in schedule_files.items():
            archive.writestr(name, data)
        archive.writestr("nested/routes.txt", schedule_files["routes.txt"])
    with pytest.raises(InputLoadError, match=r"duplicate routes\.txt"):
        load_schedule(str(duplicate))


def test_empty_schedule_source_label_is_rejected(schedule_dir: Path) -> None:
    with pytest.raises(InputLoadError, match="source label must not be empty"):
        load_schedule(str(schedule_dir), source_label="  ")
