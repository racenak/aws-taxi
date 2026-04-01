import os
import requests
import logging
import boto3
import argparse

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BASE_URL = "https://d37ci6vzurychx.cloudfront.net"

s3_client = boto3.client("s3")


def stream_download_and_upload(year: int, month: str, s3_bucket: str):
    file_name = f"yellow_tripdata_{year}-{month}.parquet"
    file_url = f"{BASE_URL}/trip-data/{file_name}"
    s3_key = f"{year}/{file_name}"

    try:
        logger.info(f"Processing {file_name}")

        with requests.get(file_url, stream=True, timeout=300) as response:
            response.raise_for_status()

            s3_client.upload_fileobj(
                response.raw,
                s3_bucket,
                s3_key,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )

        logger.info(f"Uploaded: s3://{s3_bucket}/{s3_key}")
        return True

    except Exception as e:
        logger.error(f"Error {file_name}: {str(e)}")
        return False


def main(start_year: int, end_year: int, s3_bucket: str ):
    success_count = 0

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            month_str = f"{month:02d}"
            if stream_download_and_upload(year, month_str, s3_bucket):
                success_count += 1

    logger.info(f"Finished. Uploaded {success_count} files")
    logger.info(f"Using bucket: {s3_bucket}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_year", type=int, default=2025)
    parser.add_argument("--end_year", type=int, default=2025)
    parser.add_argument("--s3_bucket", type=str, required=True, help="Target S3 Bucket name")

    args = parser.parse_args()

    main(args.start_year, args.end_year, args.s3_bucket)