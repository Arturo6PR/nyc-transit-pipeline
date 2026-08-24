select
    active.source,
    stops.stop_id,
    stops.stop_name,
    stops.stop_lat,
    stops.stop_lon,
    stops.parent_station
from {{ source('transitpulse', 'schedule_sources') }} as active
inner join {{ source('transitpulse', 'schedule_stops') }} as stops
    on active.active_schedule_id = stops.schedule_id
