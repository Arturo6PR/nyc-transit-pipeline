select *
from {{ ref('feed_quality') }}
where schedule_match_rate_pct < 95
