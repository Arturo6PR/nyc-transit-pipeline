select
    active.source,
    routes.route_id,
    routes.route_short_name,
    routes.route_long_name,
    routes.route_type
from {{ source('transitpulse', 'schedule_sources') }} as active
inner join {{ source('transitpulse', 'schedule_routes') }} as routes
    on active.active_schedule_id = routes.schedule_id
