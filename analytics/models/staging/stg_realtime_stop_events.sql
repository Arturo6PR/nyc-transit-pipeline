select
    events.event_id,
    runs.source,
    runs.feed_timestamp,
    events.entity_id,
    events.trip_id,
    events.route_id,
    events.stop_id,
    events.stop_sequence,
    events.arrival_time,
    events.arrival_delay,
    events.departure_time,
    events.departure_delay,
    coalesce(events.arrival_delay, events.departure_delay) as delay_seconds
from {{ source('transitpulse', 'trip_stop_events') }} as events
inner join {{ source('transitpulse', 'ingestion_runs') }} as runs
    on events.ingestion_id = runs.ingestion_id
