"""Upload raw Olist CSV files to the GCS landing zone."""
import argparse
import csv
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path

from google.cloud import storage

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Source filename -> table name used in the landing zone
FILE_TO_TABLE = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_name_translation",
}

LANDING_PREFIX = "olist/raw"


def count_rows(path: Path) -> int:
    """Count data rows with a CSV parser (quoted fields may contain newlines)."""
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # exclude header


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload Olist CSVs to GCS landing zone")
    parser.add_argument("--data-dir", default="data/olist")
    parser.add_argument("--ingest-date", default=date.today().isoformat(),
                        help="YYYY-MM-DD, defaults to today")
    args = parser.parse_args()

    ingest_date = date.fromisoformat(
        args.ingest_date).isoformat()  # validates format
    project_id = os.environ["GCP_PROJECT_ID"]
    bucket_name = os.environ["GCS_LANDING_BUCKET"]
    data_dir = Path(args.data_dir)

    # Fail fast: check every file exists before uploading anything
    missing = [name for name in FILE_TO_TABLE if not (
        data_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing source files in {data_dir}: {missing}")

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    manifest = {
        "ingest_date": ingest_date,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for filename, table in FILE_TO_TABLE.items():
        local_path = data_dir / filename
        blob_name = f"{LANDING_PREFIX}/{table}/ingest_date={ingest_date}/{filename}"

        bucket.blob(blob_name).upload_from_filename(
            str(local_path), content_type="text/csv")

        row_count = count_rows(local_path)
        manifest["files"].append({
            "table": table,
            "gcs_uri": f"gs://{bucket_name}/{blob_name}",
            "row_count": row_count,
            "size_bytes": local_path.stat().st_size,
        })
        logger.info("Uploaded %s (%d rows) -> gs://%s/%s",
                    filename, row_count, bucket_name, blob_name)

    manifest_name = f"{LANDING_PREFIX}/_manifests/ingest_date={ingest_date}/manifest.json"
    bucket.blob(manifest_name).upload_from_string(
        json.dumps(manifest, indent=2), content_type="application/json"
    )
    logger.info("Manifest written -> gs://%s/%s", bucket_name, manifest_name)


if __name__ == "__main__":
    main()
