with source as (
    select
        *,
        _PARTITIONDATE as ingest_date
    from {{ source('olist_raw', 'order_items') }}
    where _PARTITIONDATE = {{ latest_partition_date(source('olist_raw', 'order_items')) }}
)

select
    order_id,
    safe_cast(order_item_id as INT64) as order_item_id,
    product_id,
    seller_id,
    safe_cast(price as numeric) as price,
    safe_cast(freight_value as numeric) as freight_value,
    safe_cast(shipping_limit_date as datetime) as shipping_limit_ts,
    ingest_date
from source