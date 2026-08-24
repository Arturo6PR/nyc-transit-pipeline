select
    source,
    count(*) as event_count,
    count(*) filter (where has_schedule_match) as schedule_matched_event_count,
    count(*) filter (where not has_schedule_match) as schedule_unmatched_event_count,
    round(100.0 * avg(case when has_schedule_match then 1 else 0 end), 2) as schedule_match_rate_pct,
    count(*) filter (where delay_seconds is null) as missing_delay_event_count
from {{ ref('fct_stop_reliability') }}
group by source
