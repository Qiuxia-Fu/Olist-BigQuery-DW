with source as (
    select
        *,
        _PARTITIONDATE as ingest_date
    from {{ source('olist_raw', 'product_category_name_translation') }}
    where _PARTITIONDATE = {{ latest_partition_date(source('olist_raw', 'product_category_name_translation')) }}
)

select
    product_category_name,
    product_category_name_english,
    ingest_date
from source