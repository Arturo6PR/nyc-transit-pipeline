select
    facts.source,
    facts.stop_id,
    stops.stop_name,
    count(*) as event_count,
    round(avg(facts.delay_seconds), 2) as average_delay_seconds,
    round(quantile_cont(facts.delay_seconds, 0.95), 2) as p95_delay_seconds,
    count(*) filter (where facts.is_delayed) as delayed_event_count
from {{ ref('fct_stop_reliability') }} as facts
left join {{ ref('dim_stops') }} as stops
    on facts.source = stops.source
    and facts.stop_id = stops.stop_id
group by facts.source, facts.stop_id, stops.stop_name
