from datetime import datetime
from google.transit import gtfs_realtime_pb2


def parse_gtfs_rt(payload_bytes: bytes, feed_path: str):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload_bytes)

    rows = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip = entity.trip_update.trip

        for stu in entity.trip_update.stop_time_update:
            arrival_time = None
            delay = None

            if stu.HasField("arrival"):
                arrival_time = stu.arrival.time
                delay = stu.arrival.delay

            rows.append(
                {
                    "timestamp": datetime.utcnow(),
                    "feed_path": feed_path,
                    "trip_id": trip.trip_id,
                    "route_id": trip.route_id,
                    "stop_id": stu.stop_id,
                    "arrival_time": arrival_time,
                    "delay": delay,
                }
            )

    return rows