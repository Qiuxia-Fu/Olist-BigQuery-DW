with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select customer_id, order_purchase_ts
    from {{ ref('stg_orders') }}
)

select
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state
from customers as c
inner join orders as o
    on c.customer_id = o.customer_id
qualify row_number() over (
    partition by c.customer_unique_id
    order by o.order_purchase_ts desc, c.customer_id
) = 1