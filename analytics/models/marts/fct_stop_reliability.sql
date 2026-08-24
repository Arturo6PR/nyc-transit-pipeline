{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='delete+insert'
    )
}}

select
    realtime.event_id,
    realtime.source,
    realtime.feed_timestamp,
    date_trunc(
        'hour',
        to_timestamp(coalesce(realtime.arrival_time, realtime.departure_time, realtime.feed_timestamp))
    ) as event_hour_utc,
    realtime.entity_id,
    realtime.trip_id,
    realtime.route_id,
    realtime.stop_id,
    realtime.stop_sequence,
    scheduled.arrival_seconds as scheduled_arrival_seconds,
    scheduled.departure_seconds as scheduled_departure_seconds,
    realtime.arrival_time,
    realtime.arrival_delay,
    realtime.departure_time,
    realtime.departure_delay,
    realtime.delay_seconds,
    scheduled.trip_id is not null as has_schedule_match,
    coalesce(realtime.delay_seconds >= 300, false) as is_delayed
from {{ ref('stg_realtime_stop_events') }} as realtime
left join {{ ref('stg_schedule_stop_times') }} as scheduled
    on realtime.source = scheduled.source
    and realtime.trip_id = scheduled.trip_id
    and realtime.stop_id = scheduled.stop_id
    and realtime.stop_sequence = scheduled.stop_sequence
{% if is_incremental() %}
where realtime.event_id not in (select event_id from {{ this }})
{% endif %}
