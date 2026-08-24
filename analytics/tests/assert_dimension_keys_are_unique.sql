with route_duplicates as (
    select source, route_id
    from {{ ref('dim_routes') }}
    group by source, route_id
    having count(*) > 1
),
stop_duplicates as (
    select source, stop_id
    from {{ ref('dim_stops') }}
    group by source, stop_id
    having count(*) > 1
)

select 'route' as dimension, source, route_id as identifier from route_duplicates
union all
select 'stop' as dimension, source, stop_id as identifier from stop_duplicates
