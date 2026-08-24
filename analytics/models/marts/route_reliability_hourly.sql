select
    source,
    route_id,
    event_hour_utc,
    count(*) as event_count,
    count(*) filter (where has_schedule_match) as matched_event_count,
    round(avg(delay_seconds), 2) as average_delay_seconds,
    round(quantile_cont(delay_seconds, 0.95), 2) as p95_delay_seconds,
    count(*) filter (where is_delayed) as delayed_event_count,
    round(100.0 * avg(case when is_delayed then 1 else 0 end), 2) as delayed_event_rate_pct
from {{ ref('fct_stop_reliability') }}
group by source, route_id, event_hour_utc
