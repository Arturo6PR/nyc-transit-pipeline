"""Deterministic domain models for normalized GTFS-Realtime data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TripStopEvent:
    """One predicted arrival/departure at a stop."""

    entity_id: str
    trip_id: str
    route_id: str
    stop_id: str
    stop_sequence: int | None
    arrival_time: int | None
    arrival_delay: int | None
    departure_time: int | None
    departure_delay: int | None

    def sort_key(self) -> tuple[str, str, int, str]:
        return (
            self.route_id,
            self.trip_id,
            self.stop_sequence if self.stop_sequence is not None else -1,
            self.stop_id,
        )


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """One service-alert entity and its affected routes."""

    entity_id: str
    cause: str
    effect: str
    header_text: str | None
    description_text: str | None
    active_start: int | None
    active_end: int | None
    route_ids: tuple[str, ...]

    def sort_key(self) -> tuple[str, str, str]:
        return (self.effect, self.cause, self.entity_id)


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    """Normalized contents of one GTFS-Realtime feed message."""

    feed_timestamp: int | None
    incrementality: str
    trip_stop_events: tuple[TripStopEvent, ...]
    alerts: tuple[AlertEvent, ...]
