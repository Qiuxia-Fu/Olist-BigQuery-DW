with source as (
    select
        *,
        _PARTITIONDATE as ingest_date
    from {{ source('olist_raw', 'customers') }}
    where _PARTITIONDATE = {{ latest_partition_date(source('olist_raw', 'customers')) }}
)

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    ingest_date
from source