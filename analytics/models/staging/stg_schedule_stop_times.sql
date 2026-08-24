select
    active.source,
    stop_times.trip_id,
    stop_times.stop_sequence,
    stop_times.stop_id,
    stop_times.arrival_seconds,
    stop_times.departure_seconds
from {{ source('transitpulse', 'schedule_sources') }} as active
inner join {{ source('transitpulse', 'schedule_stop_times') }} as stop_times
    on active.active_schedule_id = stop_times.schedule_id
