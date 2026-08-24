"""Deterministic domain models for GTFS Schedule data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScheduleRoute:
    route_id: str
    route_short_name: str | None
    route_long_name: str | None
    route_type: int


@dataclass(frozen=True, slots=True)
class ScheduleTrip:
    trip_id: str
    route_id: str
    service_id: str
    trip_headsign: str | None
    direction_id: int | None


@dataclass(frozen=True, slots=True)
class ScheduleStop:
    stop_id: str
    stop_name: str
    stop_lat: float | None
    stop_lon: float | None
    parent_station: str | None


@dataclass(frozen=True, slots=True)
class ScheduleStopTime:
    trip_id: str
    stop_sequence: int
    stop_id: str
    arrival_seconds: int
    departure_seconds: int


@dataclass(frozen=True, slots=True)
class ParsedSchedule:
    routes: tuple[ScheduleRoute, ...]
    trips: tuple[ScheduleTrip, ...]
    stops: tuple[ScheduleStop, ...]
    stop_times: tuple[ScheduleStopTime, ...]
