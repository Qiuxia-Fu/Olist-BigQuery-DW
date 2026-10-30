with source as (
    select
        *,
        _PARTITIONDATE as ingest_date
    from {{ source('olist_raw', 'orders') }}
    where _PARTITIONDATE = {{ latest_partition_date(source('olist_raw', 'orders')) }}
)

select
    order_id,
    customer_id,
    order_status,
    safe_cast(order_purchase_timestamp as datetime) as order_purchase_ts,
    safe_cast(order_approved_at as datetime) as order_approved_ts,
    safe_cast(order_delivered_carrier_date as datetime) as order_delivered_carrier_ts,
    safe_cast(order_delivered_customer_date as datetime) as order_delivered_customer_ts,
    safe_cast(order_estimated_delivery_date as datetime) as order_estimated_delivery_ts,
    ingest_date
from source