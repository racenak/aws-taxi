from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.storagelevel import StorageLevel
import logging
import argparse
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Fix #4: Explicit set of operations that require a full load
FULL_LOAD_OPERATIONS = {"overwrite", "delete", "replace"}

# Aggregation output schema (used when returning an empty DataFrame)
AGG_GROUP_BY_COLS = ["pickup_year", "pickup_month", "pickup_borough", "dropoff_borough"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="NYC Yellow Taxi – Silver → Gold ETL (Full or Incremental Load)"
    )
    parser.add_argument(
        "--gold_full_ref",
        required=True,
        help="Iceberg table name. e.g.: catalog.gold.yellow_taxi",
    )
    parser.add_argument(
        "--agg_full_ref",
        required=True,
        help="Iceberg table name. e.g.: catalog.agg.yellow_taxi",
    )
    return parser.parse_args()


def validate_table_ref(ref: str) -> str:
    """Fix #8: Validate table ref to prevent SQL injection via CLI args."""
    pattern = r"^\w+\.\w+\.\w+$"
    if not re.match(pattern, ref):
        raise ValueError(
            f"Invalid table reference '{ref}'. "
            "Expected format: <catalog>.<schema>.<table>"
        )
    return ref


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("NYC_YellowTaxi_ETL_AggTable")
        .getOrCreate()
    )


def read_gold(spark: SparkSession, gold_full_ref: str):
    """
    Returns a tuple (gold_df, is_incremental):
      - gold_df:        the DataFrame to process (or None if no data)
      - is_incremental: True when only the delta was read, so the
                        writer must MERGE rather than overwrite the agg table.
    """
    logger.info("Reading Gold table: %s", gold_full_ref)

    # Fix #5: Wrap snapshot metadata query in try/except
    try:
        two_latest_snapshots = spark.sql(f"""
            SELECT snapshot_id, operation
            FROM {gold_full_ref}.snapshots
            ORDER BY committed_at DESC
            LIMIT 2
        """).collect()
    except Exception as exc:
        logger.error(
            "Failed to read snapshot metadata for '%s': %s", gold_full_ref, exc
        )
        raise

    if len(two_latest_snapshots) == 0:
        logger.warning("No snapshots found. Returning None.")
        return None, False

    latest = two_latest_snapshots[0]
    current_snapshot_id = latest["snapshot_id"]
    current_operation = latest["operation"]

    # Fix #4: Use explicit FULL_LOAD_OPERATIONS set
    # Single snapshot OR any non-append operation → full load
    if len(two_latest_snapshots) == 1 or current_operation in FULL_LOAD_OPERATIONS:
        logger.info(
            "Snapshot operation is '%s' (snapshot_id=%s). Performing full load.",
            current_operation, current_snapshot_id,
        )
        df = (
            spark.read.format("iceberg")
            .option("snapshot-id", str(current_snapshot_id))
            .load(gold_full_ref)
        )
        # Fix #3: Removed df.count() – avoid expensive full scan just for logging
        return df, False

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
        .load(gold_full_ref)
    )

    if incremental_df.isEmpty():
        logger.warning("Incremental read empty, falling back to full load.")
        return (
            spark.read.format("iceberg")
            .option("snapshot-id", str(current_snapshot_id))
            .load(gold_full_ref),
            False,
        )

    # Fix #6: Persist the incremental df (StorageLevel was imported but unused)
    incremental_df.persist(StorageLevel.MEMORY_AND_DISK)
    return incremental_df, True


def _aggregate(df):
    """Core aggregation logic, shared by full and incremental paths."""
    return df.groupBy(*AGG_GROUP_BY_COLS).agg(
        F.count("trip_id").alias("total_trips"),
        F.sum("total_amount").alias("total_revenue"),
        F.sum("trip_distance").alias("total_trip_distance"),
        F.sum("passenger_count").alias("total_passengers"),
    )


def transform(spark: SparkSession, gold_df, is_incremental: bool, agg_full_ref: str):
    """
    Fix #1: Incremental path reads the existing agg table, merges the new
    delta into it, and returns a complete aggregated DataFrame so the writer
    can safely overwrite the agg table with correct totals.
    """
    if gold_df is None:
        # Fix #7: Return a proper empty DataFrame instead of None,
        # and fix the misleading log message.
        logger.info("No Gold data available. Returning empty aggregated DataFrame.")
        return spark.createDataFrame([], schema=_make_empty_agg_schema(spark))

    logger.info("Transforming Gold data for aggregation (incremental=%s).", is_incremental)

    new_agg = _aggregate(gold_df)

    if not is_incremental:
        # Full load: new_agg already covers everything
        # Fix #3: Removed agg_df.count() – avoid extra scan just for logging
        return new_agg

    # --- Incremental merge ---
    # Fix #1: Read the existing agg table and combine with the new delta.
    try:
        existing_agg = spark.read.format("iceberg").load(agg_full_ref)
        logger.info("Existing agg table found; merging incremental delta.")
    except Exception:
        logger.warning(
            "Agg table '%s' not found or unreadable; treating as first run.",
            agg_full_ref,
        )
        return new_agg

    merged = (
        existing_agg.unionByName(new_agg)
        .groupBy(*AGG_GROUP_BY_COLS)
        .agg(
            F.sum("total_trips").alias("total_trips"),
            F.sum("total_revenue").alias("total_revenue"),
            F.sum("total_trip_distance").alias("total_trip_distance"),
            F.sum("total_passengers").alias("total_passengers"),
        )
    )
    return merged


def _make_empty_agg_schema(spark: SparkSession):
    from pyspark.sql.types import (
        StructType, StructField, IntegerType, StringType, LongType, DoubleType
    )
    return StructType([
        StructField("pickup_year", IntegerType(), True),
        StructField("pickup_month", IntegerType(), True),
        StructField("pickup_borough", StringType(), True),
        StructField("dropoff_borough", StringType(), True),
        StructField("total_trips", LongType(), True),
        StructField("total_revenue", DoubleType(), True),
        StructField("total_trip_distance", DoubleType(), True),
        StructField("total_passengers", LongType(), True),
    ])


def write_agg_table(agg_df, agg_full_ref: str):
    if agg_df is None:
        logger.info("No data to write to Agg table.")
        return

    logger.info("Writing aggregated data to Agg table: %s", agg_full_ref)
    agg_df.write.format("iceberg").mode("overwrite").save(agg_full_ref)
    logger.info("Write complete.")


def main():
    args = parse_args()

    # Fix #8: Validate table references before use
    gold_full_ref = validate_table_ref(args.gold_full_ref)
    agg_full_ref = validate_table_ref(args.agg_full_ref)

    spark = build_spark_session()
    try:
        gold_df, is_incremental = read_gold(spark, gold_full_ref)
        agg_df = transform(spark, gold_df, is_incremental, agg_full_ref)
        write_agg_table(agg_df, agg_full_ref)
    finally:
        spark.stop()


# Fix #2: Add entry-point guard so main() is actually called
if __name__ == "__main__":
    main()