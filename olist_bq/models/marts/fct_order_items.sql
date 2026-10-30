{{ config(
    materialized='table',
    partition_by={
        'field': 'order_date',
        'data_type': 'date',
        'granularity': 'month'
    },
    cluster_by=['seller_id', 'product_id']
) }}

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select customer_id, customer_unique_id
    from {{ ref('stg_customers') }}
),

dim_customers as (
    select customer_sk, customer_unique_id, effective_from, effective_to
    from {{ ref('dim_customers') }}
)

select
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    dc.customer_sk,
    c.customer_unique_id,
    date(o.order_purchase_ts) as order_date,
    o.order_status,
    o.order_purchase_ts,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value as item_total_value
from order_items as oi
inner join orders as o
    on oi.order_id = o.order_id
inner join customers as c
    on o.customer_id = c.customer_id
left join dim_customers as dc
    on c.customer_unique_id = dc.customer_unique_id
    and timestamp(o.order_purchase_ts) >= dc.effective_from
    and timestamp(o.order_purchase_ts) < dc.effective_to