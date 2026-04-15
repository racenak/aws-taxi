import argparse
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, year as spark_year, month as spark_month

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ICEBERG_TABLE = "glue_catalog.nyc_taxi.raw_yellow_taxi"

def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("NYC Yellow Taxi -> Iceberg")
        .getOrCreate()
    )

def list_s3_parquet_files(s3_bucket: str, year: int) -> list[str]:
    """List all parquet files under raw/yellow-tripdata/{year}/"""
    import boto3
    s3_client = boto3.client("s3")
    prefix = f"raw/yellow-tripdata/{year}/"

    response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    files = [
        f"s3://{s3_bucket}/{obj['Key']}"
        for obj in response.get("Contents", [])
        if obj["Key"].endswith(".parquet")
    ]

    logger.info(f"Found {len(files)} parquet file(s) under s3://{s3_bucket}/{prefix}")
    return files

def is_partition_loaded(spark: SparkSession, year: int, month: int) -> bool:
    """Check if a year/month partition already exists in the Iceberg table."""
    try:
        result = spark.sql(f"""
            SELECT COUNT(*) AS cnt
            FROM {ICEBERG_TABLE}
            WHERE pickup_year = {year} AND pickup_month = {month}
        """).collect()
        return result[0]["cnt"] > 0
    except Exception:
        return False
    
def load_parquet_to_iceberg(spark: SparkSession, s3_path: str, year: int, month: int):
    logger.info(f"Loading {s3_path} -> {ICEBERG_TABLE} (year={year}, month={month})")

    df = (
        spark.read.parquet(s3_path)
        .withColumn("pickup_year",  spark_year(col("tpep_pickup_datetime")))
        .withColumn("pickup_month", spark_month(col("tpep_pickup_datetime")))
    )

    # Filter to only the target month to avoid cross-partition writes
    df_filtered = df.filter(
        (col("pickup_year") == year) & (col("pickup_month") == month)
    )

    (
        df_filtered.writeTo(ICEBERG_TABLE)
        .option("mergeSchema", "true")
        .append()
    )

    count = spark.sql(f"""
        SELECT COUNT(*) AS cnt FROM {ICEBERG_TABLE}
        WHERE pickup_year = {year} AND pickup_month = {month}
    """).collect()[0]["cnt"]
    logger.info(f"Inserted {count:,} rows for {year}-{month:02d}")

def process_year(spark: SparkSession, s3_bucket: str, year: int):
    """Read all parquet files for a year, infer months, and load each partition."""
    files = list_s3_parquet_files(s3_bucket, year)
    if not files:
        logger.warning(f"No parquet files found for year {year}, skipping.")
        return 0

    # Read all files at once and infer year/month from timestamps
    df = (
        spark.read
        .option("mergeSchema", "true")
        .parquet(*files)
        .withColumn("pickup_year",  spark_year(col("tpep_pickup_datetime")))
        .withColumn("pickup_month", spark_month(col("tpep_pickup_datetime")))
    )

    # Discover which months are present in the data
    months_in_data = [
        row["pickup_month"]
        for row in df.select("pickup_month").distinct().orderBy("pickup_month").collect()
    ]
    logger.info(f"Months found in data for {year}: {months_in_data}")

    success_count = 0
    for month in months_in_data:
        if is_partition_loaded(spark, year, month):
            logger.info(f"Partition already loaded: {year}-{month:02d}, skipping.")
            continue

        try:
            df_month = df.filter(
                (col("pickup_year") == year) & (col("pickup_month") == month)
            )
            (
                df_month.writeTo(ICEBERG_TABLE)
                .tableProperty("write.format.default", "parquet")
                .tableProperty("write.object-storage.enabled", "false")
                .append()
            )
            count = spark.sql(f"""
                SELECT COUNT(*) AS cnt FROM {ICEBERG_TABLE}
                WHERE pickup_year = {year} AND pickup_month = {month}
            """).collect()[0]["cnt"]
            logger.info(f"Inserted {count:,} rows for {year}-{month:02d}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to load {year}-{month:02d}: {e}")

    return success_count

def main(start_year: int, end_year: int, s3_bucket: str):
    spark = create_spark_session()

    total = 0
    for year in range(start_year, end_year + 1):
        total += process_year(spark, s3_bucket, year)

    logger.info(f"Done. Loaded {total} partition(s) into {ICEBERG_TABLE}")
    spark.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_year", type=int, default=2026)
    parser.add_argument("--end_year",   type=int, default=None)
    parser.add_argument("--s3_bucket",  type=str, required=True)
    args = parser.parse_args()

    end_year = args.end_year if args.end_year is not None else args.start_year
    main(args.start_year, end_year, args.s3_bucket)