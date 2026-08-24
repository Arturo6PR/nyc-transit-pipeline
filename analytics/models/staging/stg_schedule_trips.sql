select
    active.source,
    trips.trip_id,
    trips.route_id,
    trips.service_id,
    trips.trip_headsign,
    trips.direction_id
from {{ source('transitpulse', 'schedule_sources') }} as active
inner join {{ source('transitpulse', 'schedule_trips') }} as trips
    on active.active_schedule_id = trips.schedule_id
