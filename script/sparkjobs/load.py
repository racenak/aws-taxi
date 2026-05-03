from pyspark.sql import SparkSession, DataFrame
import pyspark.sql.functions as F
from pyspark.sql.types import (
    IntegerType, StringType, TimestampType, FloatType,
    StructType, StructField,
)
from pyspark.storagelevel import StorageLevel
import logging
import argparse
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Fix #1: Explicit set of operations that require a full load
FULL_LOAD_OPERATIONS = {"overwrite", "delete", "replace"}

# Fix #6: Explicit schema for the static taxi-zone lookup CSV
TAXI_ZONE_SCHEMA = StructType([
    StructField("LocationID",    IntegerType(), True),
    StructField("Borough",       StringType(),  True),
    StructField("Zone",          StringType(),  True),
    StructField("service_zone",  StringType(),  True),
])


def parse_args():
    parser = argparse.ArgumentParser(
        description="NYC Yellow Taxi – Silver → Gold ETL (Full or Incremental Load)"
    )
    parser.add_argument(
        "--silver_full_ref",
        required=True,
        help="Iceberg table name. e.g.: catalog.silver.yellow_taxi",
    )
    parser.add_argument(
        "--gold_full_ref",
        required=True,
        help="Iceberg table name. e.g.: catalog.gold.yellow_taxi",
    )
    parser.add_argument(
        "--s3_taxi_zone_csv",
        required=True,
        help="S3 path to the taxi zone lookup CSV file",
    )
    return parser.parse_args()


# Fix #2: Shared validator – prevents SQL injection via CLI args
def validate_table_ref(ref: str) -> str:
    if not re.match(r"^\w+\.\w+\.\w+$", ref):
        raise ValueError(
            f"Invalid table reference '{ref}'. "
            "Expected format: <catalog>.<schema>.<table>"
        )
    return ref


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("NYC_YellowTaxi_ETL_Load")
        .getOrCreate()
    )


def read_silver(spark: SparkSession, silver_full_ref: str):
    """
    Returns a tuple (silver_df, current_snapshot_id).
    silver_df is None when there is nothing to process.
    """
    logger.info("Reading Silver table: %s", silver_full_ref)

    # Fix #3: Wrap snapshot metadata query in try/except
    try:
        two_latest_snapshots = spark.sql(f"""
            SELECT snapshot_id, operation
            FROM {silver_full_ref}.snapshots
            ORDER BY committed_at DESC
            LIMIT 2
        """).collect()
    except Exception as exc:
        logger.error(
            "Failed to read snapshot metadata for '%s': %s", silver_full_ref, exc
        )
        raise

    if len(two_latest_snapshots) == 0:
        logger.warning("No snapshots found. Returning None.")
        return None, None

    latest = two_latest_snapshots[0]
    current_snapshot_id = latest["snapshot_id"]
    current_operation   = latest["operation"]

    # Fix #1: Use FULL_LOAD_OPERATIONS set instead of == "overwrite"
    if len(two_latest_snapshots) == 1 or current_operation in FULL_LOAD_OPERATIONS:
        logger.info(
            "Snapshot operation is '%s' (snapshot_id=%s). Performing full load.",
            current_operation, current_snapshot_id,
        )
        df = (
            spark.read.format("iceberg")
            .option("snapshot-id", str(current_snapshot_id))
            .load(silver_full_ref)
        )
        # Fix #4: Removed df.count() – avoid expensive full scan just for logging
        return df, current_snapshot_id

    # Two append snapshots → incremental load
    previous_snapshot_id = two_latest_snapshots[1]["snapshot_id"]
    logger.info(
        "Two append snapshots found. Incremental load: %s → %s",
        previous_snapshot_id, current_snapshot_id,
    )
    incremental_df = (
        spark.read.format("iceberg")
        .option("start-snapshot-id", str(previous_snapshot_id))
        .option("end-snapshot-id", str(current_snapshot_id))
        .load(silver_full_ref)
    )

    if incremental_df.isEmpty():
        logger.warning("Incremental read empty, falling back to full load.")
        return (
            spark.read.format("iceberg")
            .option("snapshot-id", str(current_snapshot_id))
            .load(silver_full_ref),
            current_snapshot_id,
        )

    return incremental_df, current_snapshot_id


def read_taxi_zone_lookup(spark: SparkSession, s3_taxi_zone_csv: str) -> DataFrame:
    logger.info("Reading Taxi Zone Lookup CSV: %s", s3_taxi_zone_csv)

    # Fix #6: Use explicit schema instead of inferSchema=True
    # Fix #4: Removed df.count() – small file, but consistent with logging policy
    df = (
        spark.read
        .option("header", True)
        .schema(TAXI_ZONE_SCHEMA)
        .csv(s3_taxi_zone_csv)
    )
    logger.info("Taxi zone lookup loaded successfully.")
    return df


def transform(silver_df: DataFrame, taxi_zone_df: DataFrame) -> DataFrame:
    logger.info("Performing transformations for Gold layer.")

    # Fix #5: Persist and track the reference so we can unpersist later
    silver_df.persist(StorageLevel.MEMORY_AND_DISK)
    logger.info("Silver DataFrame persisted to MEMORY_AND_DISK.")

    pu_zone = taxi_zone_df.select(
        F.col("LocationID").alias("pu_loc_id"),
        F.col("Zone").alias("pickup_zone"),
        F.col("Borough").alias("pickup_borough"),
    )
    do_zone = taxi_zone_df.select(
        F.col("LocationID").alias("do_loc_id"),
        F.col("Zone").alias("dropoff_zone"),
        F.col("Borough").alias("dropoff_borough"),
    )

    # Fix #7: Alias the base DataFrame before chaining joins so that column
    # references in each join condition are unambiguous regardless of reassignment.
    base = silver_df.alias("base")

    joined_df = (
        base
        .join(F.broadcast(pu_zone), F.col("base.PULocationID") == F.col("pu_loc_id"), "left")
        .drop("pu_loc_id")
        .join(F.broadcast(do_zone), F.col("base.DOLocationID") == F.col("do_loc_id"), "left")
        .drop("do_loc_id")
    )

    gold_df = joined_df.select(
        F.sha2(
            F.concat_ws(
                "|",
                F.col("VendorID").cast(StringType()),
                F.col("tpep_pickup_datetime").cast(StringType()),
                F.col("tpep_dropoff_datetime").cast(StringType()),
                F.col("PULocationID").cast(StringType()),
                F.col("DOLocationID").cast(StringType()),
            ),
            256,
        ).alias("trip_id"),
        F.col("VendorID").cast(IntegerType()).alias("vendor_id"),
        F.col("tpep_pickup_datetime").alias("pickup_datetime"),
        F.col("tpep_dropoff_datetime").alias("dropoff_datetime"),
        F.to_date("tpep_pickup_datetime").alias("pickup_date"),
        F.year("tpep_pickup_datetime").cast(IntegerType()).alias("pickup_year"),
        F.month("tpep_pickup_datetime").cast(IntegerType()).alias("pickup_month"),
        F.dayofmonth("tpep_pickup_datetime").cast(IntegerType()).alias("pickup_day"),
        F.date_format("tpep_pickup_datetime", "EEEE").alias("pickup_day_of_week"),
        F.hour("tpep_pickup_datetime").cast(IntegerType()).alias("pickup_hour"),
        F.col("PULocationID").cast(IntegerType()).alias("pickup_location_id"),
        F.col("pickup_zone"),
        F.col("pickup_borough"),
        F.col("DOLocationID").cast(IntegerType()).alias("dropoff_location_id"),
        F.col("dropoff_zone"),
        F.col("dropoff_borough"),
        F.col("passenger_count").cast(IntegerType()),
        F.col("trip_distance").cast(FloatType()),
        F.col("total_amount").cast(FloatType()),
        F.col("payment_type").cast(IntegerType()),
        F.col("RatecodeID").cast(IntegerType()).alias("rate_code_id"),
        F.col("store_and_fwd_flag"),
        F.lit("yellow_taxi").alias("data_source"),
        # Fix #8: created_at is set only on INSERT inside the MERGE (see load_gold),
        # so we expose it here as a column that the MERGE source carries but only
        # applies to new rows, preserving idempotency on re-runs.
        F.current_timestamp().cast(TimestampType()).alias("created_at"),
    )

    logger.info("Gold transformation complete.")
    return gold_df, silver_df  # return persisted df so caller can unpersist


def load_gold(spark: SparkSession, gold_df: DataFrame, gold_full_ref: str):
    logger.info("Writing to Gold table (MERGE upsert on trip_id): %s", gold_full_ref)

    gold_df.createOrReplaceTempView("gold_incoming")

    # Fix #3: Wrap MERGE in try/except for clear error attribution
    # Fix #8: created_at is only set on INSERT, never updated on MATCH,
    #         so existing rows keep their original ingestion timestamp.
    try:
        spark.sql(f"""
            MERGE INTO {gold_full_ref} AS target
            USING gold_incoming AS source
            ON target.trip_id = source.trip_id
            WHEN MATCHED THEN UPDATE SET
                vendor_id            = source.vendor_id,
                pickup_datetime      = source.pickup_datetime,
                dropoff_datetime     = source.dropoff_datetime,
                pickup_date          = source.pickup_date,
                pickup_year          = source.pickup_year,
                pickup_month         = source.pickup_month,
                pickup_day           = source.pickup_day,
                pickup_day_of_week   = source.pickup_day_of_week,
                pickup_hour          = source.pickup_hour,
                pickup_location_id   = source.pickup_location_id,
                pickup_zone          = source.pickup_zone,
                pickup_borough       = source.pickup_borough,
                dropoff_location_id  = source.dropoff_location_id,
                dropoff_zone         = source.dropoff_zone,
                dropoff_borough      = source.dropoff_borough,
                passenger_count      = source.passenger_count,
                trip_distance        = source.trip_distance,
                total_amount         = source.total_amount,
                payment_type         = source.payment_type,
                rate_code_id         = source.rate_code_id,
                store_and_fwd_flag   = source.store_and_fwd_flag,
                data_source          = source.data_source
            WHEN NOT MATCHED THEN INSERT *
        """)
    except Exception as exc:
        logger.error("MERGE INTO '%s' failed: %s", gold_full_ref, exc)
        raise

    logger.info("MERGE INTO %s complete.", gold_full_ref)


def main():
    args = parse_args()

    # Fix #2: Validate table references before any SQL interpolation
    silver_full_ref = validate_table_ref(args.silver_full_ref)
    gold_full_ref   = validate_table_ref(args.gold_full_ref)

    logger.info("=== ETL CONFIG ===")
    logger.info("  silver_full_ref  : %s", silver_full_ref)
    logger.info("  gold_full_ref    : %s", gold_full_ref)
    logger.info("  s3_taxi_zone_csv : %s", args.s3_taxi_zone_csv)
    logger.info("==================")

    spark = build_spark_session()

    # Fix #10: Single try/finally ensures spark.stop() is always called exactly once
    persisted_silver_df = None
    try:
        silver_df, current_snapshot_id = read_silver(spark, silver_full_ref)

        if silver_df is None or silver_df.isEmpty():
            logger.info("Nothing to process. Exiting.")
            return

        taxi_zone_df = read_taxi_zone_lookup(spark, args.s3_taxi_zone_csv)

        gold_df, persisted_silver_df = transform(silver_df, taxi_zone_df)
        load_gold(spark, gold_df, gold_full_ref)

        # Fix #9: Log the actual snapshot_id that was processed
        logger.info("ETL complete. Latest processed snapshot_id: %s", current_snapshot_id)

    finally:
        # Fix #5: Always unpersist cached DataFrame to release cluster memory
        if persisted_silver_df is not None:
            persisted_silver_df.unpersist()
            logger.info("Silver DataFrame unpersisted.")
        spark.stop()


if __name__ == "__main__":
    main()