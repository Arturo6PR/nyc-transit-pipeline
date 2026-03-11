from datetime import datetime
from google.transit import gtfs_realtime_pb2


def _get_english_text(translated) -> str | None:
    """Return English translation if available, else fall back to first entry."""
    if not translated.translation:
        return None
    for t in translated.translation:
        if t.language == "en":
            return t.text
    return translated.translation[0].text


def parse_gtfs_rt(payload_bytes: bytes, feed_path: str) -> list[dict]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload_bytes)

    rows = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip = entity.trip_update.trip

        for stu in entity.trip_update.stop_time_update:
            arrival_time = None
            arrival_delay = None
            departure_time = None
            departure_delay = None

            if stu.HasField("arrival"):
                arrival_time = stu.arrival.time
                arrival_delay = stu.arrival.delay

            if stu.HasField("departure"):
                departure_time = stu.departure.time
                departure_delay = stu.departure.delay

            rows.append(
                {
                    "fetched_at": datetime.utcnow(),
                    "feed_path": feed_path,
                    "trip_id": trip.trip_id,
                    "route_id": trip.route_id,
                    "stop_id": stu.stop_id,
                    "stop_sequence": stu.stop_sequence,
                    "arrival_time": arrival_time,
                    "arrival_delay": arrival_delay,
                    "departure_time": departure_time,
                    "departure_delay": departure_delay,
                }
            )

    return rows


def parse_alerts(payload_bytes: bytes, feed_path: str) -> list[dict]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload_bytes)

    rows = []

    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue

        alert = entity.alert

        rows.append(
            {
                "fetched_at": datetime.utcnow(),
                "feed_path": feed_path,
                "alert_id": entity.id,
                "cause": gtfs_realtime_pb2.Alert.Cause.Name(alert.cause),
                "effect": gtfs_realtime_pb2.Alert.Effect.Name(alert.effect),
                "header_text": _get_english_text(alert.header_text),
                "description_text": _get_english_text(alert.description_text),
            }
        )

    return rows