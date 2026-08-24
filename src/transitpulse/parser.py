"""GTFS-Realtime protobuf normalization."""

from __future__ import annotations

from collections.abc import Iterable

from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2

from transitpulse.errors import FeedParseError
from transitpulse.models import AlertEvent, ParsedFeed, TripStopEvent


def _translated_text(translated: object) -> str | None:
    translations = list(translated.translation)  # type: ignore[attr-defined]
    if not translations:
        return None
    for translation in translations:
        if translation.language.lower().startswith("en"):
            return translation.text
    return translations[0].text


def _enum_name(enum_type: object, value: int, fallback: str = "UNKNOWN") -> str:
    try:
        return str(enum_type.Name(value))  # type: ignore[attr-defined]
    except ValueError:
        return fallback


def _optional_event_value(update: object, event_name: str, field_name: str) -> int | None:
    if not update.HasField(event_name):  # type: ignore[attr-defined]
        return None
    event = getattr(update, event_name)
    if not event.HasField(field_name):
        return None
    return int(getattr(event, field_name))


def _optional_period_value(
    periods: Iterable[object], field_name: str, *, latest: bool
) -> int | None:
    values = [int(getattr(period, field_name)) for period in periods if period.HasField(field_name)]
    if not values:
        return None
    return max(values) if latest else min(values)


def parse_feed(payload: bytes) -> ParsedFeed:
    """Parse protobuf bytes into deterministically ordered domain records."""
    if not payload:
        raise FeedParseError("feed is empty")

    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(payload)
    except DecodeError as exc:
        raise FeedParseError("input is not a valid GTFS-Realtime protobuf feed") from exc

    if not feed.header.gtfs_realtime_version:
        raise FeedParseError("feed header is missing gtfs_realtime_version")

    feed_timestamp = int(feed.header.timestamp) if feed.header.HasField("timestamp") else None
    incrementality = _enum_name(
        gtfs_realtime_pb2.FeedHeader.Incrementality,
        feed.header.incrementality,
    )

    trip_events: list[TripStopEvent] = []
    alerts: list[AlertEvent] = []

    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip = entity.trip_update.trip
            for stop_update in entity.trip_update.stop_time_update:
                trip_events.append(
                    TripStopEvent(
                        entity_id=entity.id,
                        trip_id=trip.trip_id,
                        route_id=trip.route_id,
                        stop_id=stop_update.stop_id,
                        stop_sequence=(
                            int(stop_update.stop_sequence)
                            if stop_update.HasField("stop_sequence")
                            else None
                        ),
                        arrival_time=_optional_event_value(stop_update, "arrival", "time"),
                        arrival_delay=_optional_event_value(stop_update, "arrival", "delay"),
                        departure_time=_optional_event_value(stop_update, "departure", "time"),
                        departure_delay=_optional_event_value(stop_update, "departure", "delay"),
                    )
                )

        if entity.HasField("alert"):
            alert = entity.alert
            periods = list(alert.active_period)
            route_ids = tuple(
                sorted(
                    {informed.route_id for informed in alert.informed_entity if informed.route_id}
                )
            )
            alerts.append(
                AlertEvent(
                    entity_id=entity.id,
                    cause=_enum_name(gtfs_realtime_pb2.Alert.Cause, alert.cause),
                    effect=_enum_name(gtfs_realtime_pb2.Alert.Effect, alert.effect),
                    header_text=_translated_text(alert.header_text),
                    description_text=_translated_text(alert.description_text),
                    active_start=_optional_period_value(periods, "start", latest=False),
                    active_end=_optional_period_value(periods, "end", latest=True),
                    route_ids=route_ids,
                )
            )

    return ParsedFeed(
        feed_timestamp=feed_timestamp,
        incrementality=incrementality,
        trip_stop_events=tuple(sorted(trip_events, key=TripStopEvent.sort_key)),
        alerts=tuple(sorted(alerts, key=AlertEvent.sort_key)),
    )
