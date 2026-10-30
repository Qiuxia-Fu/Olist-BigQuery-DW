select
    d as date_day,
    extract(year from d) as year,
    extract(quarter from d) as quarter,
    extract(month from d) as month,
    format_date('%B', d) as month_name,
    extract(dayofweek from d) as day_of_week,
    format_date('%A', d) as day_name,
    extract(dayofweek from d) in (1, 7) as is_weekend
from unnest(generate_date_array('2016-01-01', '2018-12-31')) as d