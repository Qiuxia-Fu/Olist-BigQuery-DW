with source as (
    select
        *,
        _PARTITIONDATE as ingest_date
    from {{ source('olist_raw', 'sellers') }}
    where _PARTITIONDATE = {{ latest_partition_date(source('olist_raw', 'sellers')) }}
)

select
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    ingest_date
from source