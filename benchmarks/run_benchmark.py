"""Benchmark partitioning and clustering effects on BigQuery bytes processed/billed."""
import argparse
import csv
import logging
import os
from pathlib import Path

from google.cloud import bigquery

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LOCATION = "europe-north2"
DATASET = "benchmark"
SOURCE_TABLE = "dbt_dev_marts.fct_order_items"
MAX_BYTES_BILLED = 10 * 1024**3  # safety cap per query: 10 GiB

# Three tables with identical data, different storage layout
TABLE_LAYOUTS = {
    "fct_plain": "",
    "fct_part": "partition by date_trunc(order_date, month)",
    "fct_part_clust": "partition by date_trunc(order_date, month) cluster by seller_id, product_id",
}

QUERIES = {
    "Q1_select_star": "select * from `{table}`",
    "Q2_two_columns": "select order_date, sum(price) as revenue from `{table}` group by order_date",
    "Q3_one_month": (
        "select sum(price) as revenue from `{table}` "
        "where order_date between '2018-01-01' and '2018-01-31'"
    ),
    "Q4_one_seller": "select sum(price) as revenue from `{table}` where seller_id = '{seller_id}'",
    "Q5_seller_and_month": (
        "select sum(price) as revenue from `{table}` "
        "where seller_id = '{seller_id}' and order_date between '2018-01-01' and '2018-01-31'"
    ),
}


def build_tables(client: bigquery.Client, project: str, scale: int) -> None:
    """Create the benchmark dataset and three scaled-up copies of the fact table."""
    dataset = bigquery.Dataset(f"{project}.{DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)

    for name, layout in TABLE_LAYOUTS.items():
        sql = f"""
            create or replace table `{project}.{DATASET}.{name}`
            {layout}
            as
            select
                f.* except (order_id),
                concat(f.order_id, '-', cast(copy_id as string)) as order_id,
                copy_id
            from `{project}.{SOURCE_TABLE}` as f,
                unnest(generate_array(1, {scale})) as copy_id
        """
        client.query(sql, location=LOCATION).result()
        table = client.get_table(f"{project}.{DATASET}.{name}")
        logger.info("Built %s: %d rows, %.1f MB", name,
                    table.num_rows, table.num_bytes / 1e6)


def pick_seller(client: bigquery.Client, project: str) -> str:
    """Pick a mid-sized seller so the filter is selective but not trivial."""
    sql = f"""
        select seller_id
        from `{project}.{SOURCE_TABLE}`
        group by seller_id
        order by count(*) desc
        limit 1 offset 50
    """
    return list(client.query(sql, location=LOCATION).result())[0].seller_id


def run_query(client: bigquery.Client, sql: str, dry_run: bool) -> bigquery.QueryJob:
    config = bigquery.QueryJobConfig(
        dry_run=dry_run,
        use_query_cache=False,
        maximum_bytes_billed=MAX_BYTES_BILLED,
    )
    job = client.query(sql, job_config=config, location=LOCATION)
    if not dry_run:
        job.result()
    return job


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BigQuery partition/cluster benchmark")
    parser.add_argument("--scale", type=int, default=100,
                        help="how many copies of the fact table")
    parser.add_argument("--skip-build", action="store_true",
                        help="reuse existing benchmark tables")
    args = parser.parse_args()

    project = os.environ["GCP_PROJECT_ID"]
    client = bigquery.Client(project=project)

    if not args.skip_build:
        build_tables(client, project, args.scale)

    seller_id = pick_seller(client, project)
    logger.info("Seller used in filters: %s", seller_id)

    results = []
    for table_name in TABLE_LAYOUTS:
        table = f"{project}.{DATASET}.{table_name}"
        for query_name, template in QUERIES.items():
            sql = template.format(table=table, seller_id=seller_id)
            dry = run_query(client, sql, dry_run=True)
            real = run_query(client, sql, dry_run=False)
            row = {
                "table": table_name,
                "query": query_name,
                "dry_run_mb": round(dry.total_bytes_processed / 1e6, 1),
                "processed_mb": round(real.total_bytes_processed / 1e6, 1),
                "billed_mb": round(real.total_bytes_billed / 1e6, 1),
                "slot_ms": real.slot_millis,
                "elapsed_ms": int((real.ended - real.started).total_seconds() * 1000),
            }
            results.append(row)
            logger.info("%s / %s: %s", table_name, query_name, row)

    out = Path(__file__).parent / "results.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    logger.info("Results written to %s", out)


if __name__ == "__main__":
    main()
