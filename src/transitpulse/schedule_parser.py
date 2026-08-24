"""Strict, deterministic parsing for the TransitPulse GTFS Schedule subset."""

from __future__ import annotations

import csv
import io
import re

from transitpulse.errors import FeedParseError
from transitpulse.schedule_models import (
    ParsedSchedule,
    ScheduleRoute,
    ScheduleStop,
    ScheduleStopTime,
    ScheduleTrip,
)

TIME_PATTERN = re.compile(r"^(\d+):([0-5]\d):([0-5]\d)$")


def _read_rows(data: bytes, filename: str, required_fields: set[str]) -> list[dict[str, str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FeedParseError(f"{filename} must be UTF-8 encoded") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = set(reader.fieldnames or ())
    missing = sorted(required_fields - headers)
    if missing:
        raise FeedParseError(f"{filename} is missing fields: {', '.join(missing)}")
    rows = [
        {str(key): (value or "").strip() for key, value in row.items() if key is not None}
        for row in reader
        if any((value or "").strip() for value in row.values())
    ]
    if not rows:
        raise FeedParseError(f"{filename} contains no data rows")
    return rows


def _required(row: dict[str, str], field: str, filename: str, row_number: int) -> str:
    value = row.get(field, "")
    if not value:
        raise FeedParseError(f"{filename} row {row_number} has an empty {field}")
    return value


def _optional(value: str) -> str | None:
    return value or None


def _integer(value: str, field: str, filename: str, row_number: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise FeedParseError(f"{filename} row {row_number} has invalid {field}: {value}") from exc


def _coordinate(
    value: str,
    field: str,
    filename: str,
    row_number: int,
    minimum: float,
    maximum: float,
) -> float | None:
    if not value:
        return None
    try:
        coordinate = float(value)
    except ValueError as exc:
        raise FeedParseError(f"{filename} row {row_number} has invalid {field}: {value}") from exc
    if not minimum <= coordinate <= maximum:
        raise FeedParseError(f"{filename} row {row_number} has out-of-range {field}: {value}")
    return coordinate


def _time_seconds(value: str, field: str, row_number: int) -> int:
    match = TIME_PATTERN.fullmatch(value)
    if match is None:
        raise FeedParseError(f"stop_times.txt row {row_number} has invalid {field}: {value}")
    hours, minutes, seconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def parse_schedule(files: dict[str, bytes]) -> ParsedSchedule:
    route_rows = _read_rows(
        files["routes.txt"],
        "routes.txt",
        {"route_id", "route_short_name", "route_long_name", "route_type"},
    )
    routes: list[ScheduleRoute] = []
    route_ids: set[str] = set()
    for row_number, row in enumerate(route_rows, start=2):
        route_id = _required(row, "route_id", "routes.txt", row_number)
        if route_id in route_ids:
            raise FeedParseError(f"routes.txt contains duplicate route_id: {route_id}")
        short_name = _optional(row.get("route_short_name", ""))
        long_name = _optional(row.get("route_long_name", ""))
        if short_name is None and long_name is None:
            raise FeedParseError(
                f"routes.txt row {row_number} needs route_short_name or route_long_name"
            )
        route_type = _integer(
            _required(row, "route_type", "routes.txt", row_number),
            "route_type",
            "routes.txt",
            row_number,
        )
        routes.append(ScheduleRoute(route_id, short_name, long_name, route_type))
        route_ids.add(route_id)

    trip_rows = _read_rows(
        files["trips.txt"],
        "trips.txt",
        {"route_id", "service_id", "trip_id"},
    )
    trips: list[ScheduleTrip] = []
    trip_ids: set[str] = set()
    for row_number, row in enumerate(trip_rows, start=2):
        trip_id = _required(row, "trip_id", "trips.txt", row_number)
        route_id = _required(row, "route_id", "trips.txt", row_number)
        if trip_id in trip_ids:
            raise FeedParseError(f"trips.txt contains duplicate trip_id: {trip_id}")
        if route_id not in route_ids:
            raise FeedParseError(f"trips.txt references unknown route_id: {route_id}")
        direction_text = row.get("direction_id", "")
        direction_id = (
            _integer(direction_text, "direction_id", "trips.txt", row_number)
            if direction_text
            else None
        )
        if direction_id not in {None, 0, 1}:
            raise FeedParseError(
                f"trips.txt row {row_number} has invalid direction_id: {direction_id}"
            )
        trips.append(
            ScheduleTrip(
                trip_id=trip_id,
                route_id=route_id,
                service_id=_required(row, "service_id", "trips.txt", row_number),
                trip_headsign=_optional(row.get("trip_headsign", "")),
                direction_id=direction_id,
            )
        )
        trip_ids.add(trip_id)

    stop_rows = _read_rows(
        files["stops.txt"],
        "stops.txt",
        {"stop_id", "stop_name"},
    )
    stops: list[ScheduleStop] = []
    stop_ids: set[str] = set()
    for row_number, row in enumerate(stop_rows, start=2):
        stop_id = _required(row, "stop_id", "stops.txt", row_number)
        if stop_id in stop_ids:
            raise FeedParseError(f"stops.txt contains duplicate stop_id: {stop_id}")
        stops.append(
            ScheduleStop(
                stop_id=stop_id,
                stop_name=_required(row, "stop_name", "stops.txt", row_number),
                stop_lat=_coordinate(
                    row.get("stop_lat", ""), "stop_lat", "stops.txt", row_number, -90, 90
                ),
                stop_lon=_coordinate(
                    row.get("stop_lon", ""), "stop_lon", "stops.txt", row_number, -180, 180
                ),
                parent_station=_optional(row.get("parent_station", "")),
            )
        )
        stop_ids.add(stop_id)
    for stop in stops:
        if stop.parent_station is not None and stop.parent_station not in stop_ids:
            raise FeedParseError(
                f"stops.txt references unknown parent_station: {stop.parent_station}"
            )

    stop_time_rows = _read_rows(
        files["stop_times.txt"],
        "stop_times.txt",
        {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"},
    )
    stop_times: list[ScheduleStopTime] = []
    stop_time_keys: set[tuple[str, int]] = set()
    for row_number, row in enumerate(stop_time_rows, start=2):
        trip_id = _required(row, "trip_id", "stop_times.txt", row_number)
        stop_id = _required(row, "stop_id", "stop_times.txt", row_number)
        if trip_id not in trip_ids:
            raise FeedParseError(f"stop_times.txt references unknown trip_id: {trip_id}")
        if stop_id not in stop_ids:
            raise FeedParseError(f"stop_times.txt references unknown stop_id: {stop_id}")
        sequence = _integer(
            _required(row, "stop_sequence", "stop_times.txt", row_number),
            "stop_sequence",
            "stop_times.txt",
            row_number,
        )
        if sequence < 0:
            raise FeedParseError(
                f"stop_times.txt row {row_number} has negative stop_sequence: {sequence}"
            )
        key = (trip_id, sequence)
        if key in stop_time_keys:
            raise FeedParseError(
                f"stop_times.txt contains duplicate trip_id/stop_sequence: {trip_id}/{sequence}"
            )
        arrival_text = row.get("arrival_time", "") or row.get("departure_time", "")
        departure_text = row.get("departure_time", "") or row.get("arrival_time", "")
        if not arrival_text or not departure_text:
            raise FeedParseError(
                f"stop_times.txt row {row_number} needs arrival_time or departure_time"
            )
        arrival_seconds = _time_seconds(arrival_text, "arrival_time", row_number)
        departure_seconds = _time_seconds(departure_text, "departure_time", row_number)
        if departure_seconds < arrival_seconds:
            raise FeedParseError(f"stop_times.txt row {row_number} departs before it arrives")
        stop_times.append(
            ScheduleStopTime(
                trip_id=trip_id,
                stop_sequence=sequence,
                stop_id=stop_id,
                arrival_seconds=arrival_seconds,
                departure_seconds=departure_seconds,
            )
        )
        stop_time_keys.add(key)

    previous_by_trip: dict[str, ScheduleStopTime] = {}
    for stop_time in sorted(stop_times, key=lambda item: (item.trip_id, item.stop_sequence)):
        previous = previous_by_trip.get(stop_time.trip_id)
        if previous is not None and stop_time.arrival_seconds < previous.departure_seconds:
            raise FeedParseError(
                f"stop_times.txt has decreasing times for trip_id: {stop_time.trip_id}"
            )
        previous_by_trip[stop_time.trip_id] = stop_time

    return ParsedSchedule(
        routes=tuple(sorted(routes, key=lambda route: route.route_id)),
        trips=tuple(sorted(trips, key=lambda trip: trip.trip_id)),
        stops=tuple(sorted(stops, key=lambda stop: stop.stop_id)),
        stop_times=tuple(
            sorted(stop_times, key=lambda stop_time: (stop_time.trip_id, stop_time.stop_sequence))
        ),
    )
