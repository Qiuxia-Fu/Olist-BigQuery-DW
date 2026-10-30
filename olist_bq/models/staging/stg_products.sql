with source as (
    select
        *,
        _PARTITIONDATE as ingest_date
    from {{ source('olist_raw', 'products') }}
    where _PARTITIONDATE = {{ latest_partition_date(source('olist_raw', 'products')) }}
)

select
    product_id,
    product_category_name,
    safe_cast(safe_cast(product_name_lenght as numeric) as int64) as product_name_length,
    safe_cast(safe_cast(product_description_lenght as numeric) as int64) as product_description_length,
    safe_cast(safe_cast(product_photos_qty as numeric) as int64) as product_photos_qty,
    safe_cast(safe_cast(product_weight_g as numeric) as int64) as product_weight_g,
    safe_cast(safe_cast(product_length_cm as numeric) as int64) as product_length_cm,
    safe_cast(safe_cast(product_height_cm as numeric) as int64) as product_height_cm,
    safe_cast(safe_cast(product_width_cm as numeric) as int64) as product_width_cm, 
    ingest_date
from source