"""Load one ingest_date batch from the GCS landing zone into BigQuery raw tables."""
import argparse
import csv
import io
import json
import logging
import os
from datetime import date

from google.cloud import bigquery, storage

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LANDING_PREFIX = "olist/raw"


def read_manifest(storage_client: storage.Client, bucket_name: str, ingest_date: str) -> dict:
    blob_name = f"{LANDING_PREFIX}/_manifests/ingest_date={ingest_date}/manifest.json"
    blob = storage_client.bucket(bucket_name).blob(blob_name)
    return json.loads(blob.download_as_text())


def schema_from_header(storage_client: storage.Client, gcs_uri: str) -> list[bigquery.SchemaField]:
    """Build an all-STRING schema from the CSV header (raw layer keeps data as-is)."""
    blob = storage.Blob.from_string(gcs_uri, client=storage_client)
    head = blob.download_as_bytes(
        start=0, end=8191).decode("utf-8", errors="ignore")
    header = next(csv.reader(io.StringIO(head)))
    # strip a UTF-8 byte order mark if present
    header[0] = header[0].lstrip("\ufeff")
    return [bigquery.SchemaField(col, "STRING") for col in header]


def ensure_table(bq_client: bigquery.Client, table_id: str, schema: list) -> None:
    """Create an ingestion-time partitioned table if it does not exist yet."""
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY)
    bq_client.create_table(table, exists_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load a landing-zone batch into BigQuery raw tables")
    parser.add_argument(
        "--ingest-date", default=date.today().isoformat(), help="YYYY-MM-DD")
    args = parser.parse_args()

    ingest_date = date.fromisoformat(args.ingest_date).isoformat()
    partition = ingest_date.replace("-", "")  # 2026-10-29 -> 20261029
    project_id = os.environ["GCP_PROJECT_ID"]
    bucket_name = os.environ["GCS_LANDING_BUCKET"]
    dataset = os.environ.get("BQ_RAW_DATASET", "olist_raw")

    storage_client = storage.Client(project=project_id)
    bq_client = bigquery.Client(project=project_id)

    manifest = read_manifest(storage_client, bucket_name, ingest_date)
    mismatches = []

    for entry in manifest["files"]:
        table_id = f"{project_id}.{dataset}.{entry['table']}"
        schema = schema_from_header(storage_client, entry["gcs_uri"])
        ensure_table(bq_client, table_id, schema)

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            schema=schema,
            skip_leading_rows=1,
            allow_quoted_newlines=True,  # review comments contain newlines inside quotes
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        # partition decorator: replace only this day
        destination = f"{table_id}${partition}"
        job = bq_client.load_table_from_uri(
            entry["gcs_uri"], destination, job_config=job_config)
        job.result()  # wait for completion; raises on failure

        loaded, expected = job.output_rows, entry["row_count"]
        logger.info("Loaded %s: %d rows (manifest: %d)",
                    destination, loaded, expected)
        if loaded != expected:
            mismatches.append(
                f"{entry['table']}: loaded {loaded}, expected {expected}")

    if mismatches:
        raise RuntimeError(f"Row count reconciliation failed: {mismatches}")
    logger.info("All %d tables reconciled for ingest_date=%s",
                len(manifest["files"]), ingest_date)


if __name__ == "__main__":
    main()
