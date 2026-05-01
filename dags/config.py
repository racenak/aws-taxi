"""
NYC Yellow Taxi ETL - Configuration & Variables

To use the taxi_etl_dag.py, set these Airflow Variables in the UI or CLI.
Example CLI setup:

    airflow variables set taxi_s3_bucket "my-taxi-bucket"
    airflow variables set taxi_s3_raw_prefix "raw/taxi"
    airflow variables set taxi_s3_bronze_prefix "bronze/taxi"
    airflow variables set iceberg_catalog "prod_catalog"
    airflow variables set taxi_zone_csv_path "s3://my-bucket/lookup/taxi-zones.csv"
"""

import json

# ============================================================================
# Airflow Variables Configuration
# ============================================================================

AIRFLOW_VARIABLES = {
    # S3 Configuration
    "taxi_s3_bucket": {
        "value": "taxi-data-bucket",
        "description": "S3 bucket name for taxi data storage",
    },
    "taxi_s3_raw_prefix": {
        "value": "raw/taxi",
        "description": "S3 prefix for raw (ingest) data",
    },
    "taxi_s3_bronze_prefix": {
        "value": "bronze/taxi",
        "description": "S3 prefix for bronze (raw downloaded) data",
    },
    # Iceberg Configuration
    "iceberg_catalog": {
        "value": "nycatalog",
        "description": "Iceberg catalog name (e.g., nycatalog)",
    },
    # Lookup Data
    "taxi_zone_csv_path": {
        "value": "s3://taxi-data-bucket/lookup/taxi-zones.csv",
        "description": "S3 path to taxi zone lookup CSV",
    },
    # Job Scripts
    "taxi_download_script": {
        "value": "/opt/airflow/jobs/taxi-download/download_with_partition.py",
        "description": "Path to taxi download script",
    },
    "clean_script": {
        "value": "/opt/airflow/jobs/job/clean.py",
        "description": "Path to clean/validate script (Bronze → Silver)",
    },
    "load_script": {
        "value": "/opt/airflow/jobs/job/load.py",
        "description": "Path to load script (Silver → Gold)",
    },
    "agg_script": {
        "value": "/opt/airflow/jobs/job/agg_table.py",
        "description": "Path to aggregation script (Gold → Agg)",
    },
}

# ============================================================================
# Setup Commands
# ============================================================================


def print_setup_commands():
    """Print CLI commands to set up all variables."""
    print("\n=== Airflow Variables Setup Commands ===\n")
    for var_name, var_config in AIRFLOW_VARIABLES.items():
        value = var_config["value"]
        print(f'airflow variables set "{var_name}" "{value}"')
    print("\n")


if __name__ == "__main__":
    print_setup_commands()
