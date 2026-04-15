import os
import logging
import tempfile
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_file_name(year: int, month: int) -> str:
    """Return the expected parquet filename for a given year/month."""
    return f"yellow_tripdata_{year}-{month:02d}.parquet"


def build_download_url(filename: str) -> str:
    return f"https://d37ci6vzurychx.cloudfront.net/trip-data/{filename}"


def build_s3_key(prefix: str, download_date: date, filename: str) -> str:
    """
    Partition key by download date.
    Example: taxi/yellow/year=2026/month=04/day=16/yellow_tripdata_2026-03.parquet
    """
    return (
        f"{prefix}/"
        f"year={download_date.year}/"
        f"month={download_date.month:02d}/"
        f"day={download_date.day:02d}/"
        f"{filename}"
    )


def download_to_temp(url: str) -> str:
    """Stream-download a URL to a named temporary file."""
    log.info("Downloading: %s", url)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        log.info("File size: %.1f MB", total / 1024 / 1024 if total else 0)

        suffix = os.path.splitext(url)[-1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
            if chunk:
                tmp.write(chunk)
                downloaded += len(chunk)
        tmp.flush()
        tmp.close()

    log.info("Downloaded %.1f MB → %s", downloaded / 1024 / 1024, tmp.name)
    return tmp.name


def s3_key_exists(bucket: str, key: str) -> bool:
    """Return True if the S3 key already exists."""
    s3 = boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            return False
        raise


def upload_to_s3(local_path: str, bucket: str, key: str) -> None:
    """Upload file to S3."""
    s3 = boto3.client("s3")
    log.info("Uploading to s3://%s/%s", bucket, key)
    try:
        s3.upload_file(
            local_path,
            bucket,
            key,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )
        log.info("Upload complete.")
    except (BotoCoreError, ClientError) as exc:
        log.error("S3 upload failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(target_year: int, bucket: str , prefix: str ) -> dict:
    """
    Download NYC Yellow Taxi data to S3.
    
    - Nếu có target_year → tải toàn bộ 12 tháng của năm đó.
    - Nếu không → tải tháng trước (previous month).
    """
    if not bucket:
        raise ValueError("S3 Bucket is required. Please provide --bucket")
    if not prefix:
        prefix = "taxi/yellow"   # default nếu không truyền --prefix

    download_date = date.today()

    if target_year is None:
        # Default: previous month
        prev = datetime.today().replace(day=1) - relativedelta(months=1)
        target_year = prev.year
        months = [prev.month]
        log.info("Running in monthly mode (previous month)")
    else:
        months = list(range(1, 13))
        log.info("Running in yearly mode for year %d", target_year)

    results = []

    for month in months:
        filename = build_file_name(target_year, month)
        url = build_download_url(filename)
        s3_key = build_s3_key(prefix, download_date, filename)

        log.info("=== NYC Yellow Taxi Downloader ===")
        log.info("Target data  : %04d-%02d", target_year, month)
        log.info("Download date: %s", download_date.isoformat())
        log.info("Source URL   : %s", url)
        log.info("Destination  : s3://%s/%s", bucket, s3_key)

        # Skip if already exists
        if s3_key_exists(bucket, s3_key):
            result = {
                "status": "skipped",
                "reason": "File already exists in S3",
                "s3_uri": f"s3://{bucket}/{s3_key}",
                "year": target_year,
                "month": month,
            }
            log.info("Skipping — file already exists")
            results.append(result)
            continue

        tmp_path = None
        try:
            tmp_path = download_to_temp(url)
            upload_to_s3(tmp_path, bucket, s3_key)
            result = {
                "status": "success",
                "source_url": url,
                "s3_uri": f"s3://{bucket}/{s3_key}",
                "year": target_year,
                "month": month,
            }
            log.info("Done.")
            results.append(result)
        except Exception as exc:
            log.error("Failed for %04d-%02d: %s", target_year, month, exc)
            results.append({"status": "failed", "year": target_year, "month": month, "error": str(exc)})
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                log.info("Temp file cleaned up.")

    return {"status": "completed", "results": results}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download NYC Yellow Taxi data to S3.")
    
    parser.add_argument("--year",   type=int, help="Data year (if provided → download all 12 months)")
    parser.add_argument("--bucket", type=str, required=True, 
                        help="S3 Bucket name (REQUIRED)")
    parser.add_argument("--prefix", type=str, default="raw/taxi",
                        help="S3 Prefix (default: raw/taxi)")
    
    args = parser.parse_args()

    run(
        target_year=args.year,
        bucket=args.bucket,
        prefix=args.prefix
    )