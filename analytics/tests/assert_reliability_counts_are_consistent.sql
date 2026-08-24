select *
from {{ ref('route_reliability_hourly') }}
where delayed_event_count > event_count
   or matched_event_count > event_count
   or delayed_event_rate_pct < 0
   or delayed_event_rate_pct > 100
