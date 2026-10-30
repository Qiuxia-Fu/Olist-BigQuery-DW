select
    dbt_scd_id as customer_sk,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    case
        when row_number() over (
            partition by customer_unique_id order by dbt_valid_from
        ) = 1 then timestamp '1900-01-01'
        else dbt_valid_from
    end as effective_from,
    coalesce(dbt_valid_to, timestamp '9999-12-31') as effective_to,
    dbt_valid_to is null as is_current
from {{ ref('customers_snapshot') }}