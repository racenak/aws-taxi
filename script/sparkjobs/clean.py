from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit
from pyspark.storagelevel import StorageLevel
import logging
import argparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ARGUMENT PARSER
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="NYC Yellow Taxi – Raw → Silver ETL (Full or Incremental Load)"
    )
    parser.add_argument(
        "--bronze-path",
        required=True,
        help="S3 URI of the Bronze folder containing Parquet files."
    )
    parser.add_argument(
        "--silver_full_ref",
        required=True,
        help="Iceberg table name. e.g.: catalog.silver.yellow_taxi",
    )
    parser.add_argument(
        "--incremental-col",
        default="tpep_pickup_datetime",
        help="Column used as the high-water mark for incremental loads.",
    )
    return parser.parse_args()

def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("NYC_YellowTaxi_ETL_Clean")
        .getOrCreate()
    )

# ─────────────────────────────────────────────
# EXTRACT  –  read Bronze
# ─────────────────────────────────────────────
def read_bronze(spark: SparkSession, bronze_path: str, incremental_col: str, watermark: str):
    logger.info("Reading Bronze from: %s", bronze_path)
    logger.info("Applying watermark filter: %s > %s", incremental_col, watermark)
    
    return spark.read.parquet(bronze_path).filter(col(incremental_col) > watermark)

# ─────────────────────────────────────────────
# TRANSFORM  –  clean Bronze
# ─────────────────────────────────────────────
def clean_and_validate(df, incremental_col: str):
    logger.info("Performing data quality checks")

    # 1. Global DQ + early payment filter
    df = df.filter(
        col("PULocationID").isNotNull() & (col("PULocationID") != 0) & 
        col("DOLocationID").isNotNull() & (col("DOLocationID") != 0) &
        (~col("PULocationID").isin([264, 265])) &
        (~col("DOLocationID").isin([264, 265])) &
        col("tpep_pickup_datetime").isNotNull() &
        col("tpep_dropoff_datetime").isNotNull() &
        (col("tpep_dropoff_datetime") > col("tpep_pickup_datetime")) &
        (col("total_amount") > 0) &
        (col("trip_distance") >= 0) &
        col("payment_type").isin([1, 2])
    )

    # 2. Cache
    df.persist(StorageLevel.MEMORY_AND_DISK)
    
    # 3. Per-RatecodeID rules
    final_df = df.filter(
        col("RatecodeID").isin([1, 2, 3, 4, 5]) &
        when(col("RatecodeID") == 1,
            (col("improvement_surcharge") == 1.0) &
            (col("mta_tax").isin([0.0, 0.5])) &
            (col("congestion_surcharge").isin([0.0, 2.5])) &
            (col("fare_amount") >= 3.0) &
            (col("cbd_congestion_fee").isin([0.0, 0.75]))
        ).when(col("RatecodeID") == 2,
            (col("Airport_fee") >= 0.0) &
            (col("mta_tax").isin([0.0, 0.5])) &
            (col("improvement_surcharge").isin([0.0, 1.0])) &
            (col("congestion_surcharge").isin([0.0, 2.5])) &
            (col("cbd_congestion_fee").isin([0.0, 0.75]))
        ).when(col("RatecodeID") == 3,
            (col("fare_amount") >= 0.0) &
            (col("improvement_surcharge") >= 0.0)
        ).when(col("RatecodeID") == 4,
            (col("mta_tax") == 0.5) &
            (col("improvement_surcharge") == 1.0) &
            (col("congestion_surcharge").isin([0.0, 2.5])) &
            (col("cbd_congestion_fee").isin([0.0, 0.75]))
        ).when(col("RatecodeID") == 5,
            (col("mta_tax").isin([0.0, 0.5])) &
            (col("improvement_surcharge") == 1.0) &
            (col("congestion_surcharge").isin([0.0, 2.5])) &
            (col("cbd_congestion_fee").isin([0.0, 0.75]))
        ).otherwise(False)
    ).sortWithinPartitions(incremental_col)

    # 4. Release cache
    df.unpersist()
    return final_df

# ─────────────────────────────────────────────
# LOAD & HELPERS
# ─────────────────────────────────────────────
def get_silver_watermark(spark: SparkSession, silver_full_ref: str, incremental_col: str):
    row = spark.sql(f"SELECT MAX({incremental_col}) AS wm FROM {silver_full_ref}").collect()[0]
    watermark = row["wm"]
    if watermark is None:
        logger.info("Silver table is empty. Will perform FULL LOAD.")
        return None
    logger.info("Silver watermark (%s): %s", incremental_col, watermark)
    return watermark

def full_load_to_silver(df, silver_full_ref: str):
    logger.info("Performing FULL LOAD to Silver: %s", silver_full_ref)
    df.writeTo(silver_full_ref).overwrite(lit(True))

def append_to_silver(df, silver_full_ref: str):
    logger.info("Appending incremental data to Silver: %s", silver_full_ref)
    df.writeTo(silver_full_ref).append()

# ─────────────────────────────────────────────
# MAIN EXECUTOR
# ─────────────────────────────────────────────
def main():
    args = parse_args()
    logger.info("=== ETL CONFIG ===")
    logger.info("  bronze_path     : %s", args.bronze_path)
    logger.info("  silver_full_ref : %s", args.silver_full_ref)
    logger.info("  incremental_col : %s", args.incremental_col)
    logger.info("==================")

    spark = build_spark_session()

    # 1. Get Watermark from Silver table
    watermark = get_silver_watermark(spark, args.silver_full_ref, args.incremental_col)
    
    # 2. Read Bronze data based on whether it's full or incremental load
    if watermark is None:
        # FULL LOAD: Read all Bronze data
        logger.info("Reading all Bronze data for FULL LOAD...")
        bronze_df = spark.read.parquet(args.bronze_path)
        load_type = "FULL"
    else:
        # INCREMENTAL LOAD: Read only new data
        logger.info("Reading incremental Bronze data since: %s", watermark)
        bronze_df = read_bronze(spark, args.bronze_path, args.incremental_col, watermark)
        load_type = "INCREMENTAL"

    # 3. Check if there's any data to process
    row_count = bronze_df.count()
    if row_count == 0:
        logger.info("No records found in Bronze. Nothing to load.")
        spark.stop()
        return

    logger.info("%s LOAD: %d records found in Bronze", load_type, row_count)
    
    # 4. Clean and validate
    silver_df = clean_and_validate(bronze_df, args.incremental_col)
    
    # 5. Load to Silver (full or incremental)
    if watermark is None:
        full_load_to_silver(silver_df, args.silver_full_ref)
    else:
        append_to_silver(silver_df, args.silver_full_ref)

    # 6. Log final row count
    total = spark.sql(f"SELECT COUNT(1) AS cnt FROM {args.silver_full_ref}").collect()[0]["cnt"]
    logger.info("Silver table total row count after %s load: %d", load_type, total)

    spark.stop()
    logger.info("ETL pipeline finished successfully (%s LOAD).", load_type)

if __name__ == "__main__":
    main()