select
    source,
    stop_id,
    stop_name,
    stop_lat,
    stop_lon,
    parent_station
from {{ ref('stg_schedule_stops') }}
