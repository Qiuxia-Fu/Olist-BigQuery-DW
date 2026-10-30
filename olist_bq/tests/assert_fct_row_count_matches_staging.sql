with fct as (
    select count(*) as n from {{ ref('fct_order_items') }}
),

stg as (
    select count(*) as n from {{ ref('stg_order_items') }}
)

select fct.n as fct_rows, stg.n as stg_rows
from fct, stg
where fct.n != stg.n