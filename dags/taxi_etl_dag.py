"""
NYC Yellow Taxi ETL Pipeline DAG

This DAG orchestrates the complete ETL pipeline:
1. Ingest: Download taxi data from public source to S3 (Bronze)
2. Transform: Clean/validate data (Bronze → Silver)
3. Load: Enrich with taxi zone info (Silver → Gold)
4. Aggregate: Create aggregated views (Gold → Agg)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable

# ============================================================================
# Default Args
# ============================================================================

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# ============================================================================
# DAG Definition
# ============================================================================

dag = DAG(
    "taxi_etl_pipeline",
    default_args=default_args,
    description="NYC Yellow Taxi ETL Pipeline (Ingest → Transform → Load)",
    schedule_interval="@weekly",  # Run weekly; adjust as needed
    catchup=False,
    tags=["etl", "taxi", "iceberg"],
)

# ============================================================================
# Configuration from Airflow Variables
# ============================================================================

# S3 Configuration
S3_BUCKET = Variable.get("taxi_s3_bucket", default_var="taxi-data-bucket")
S3_RAW_PREFIX = Variable.get("taxi_s3_raw_prefix", default_var="raw/taxi")
S3_BRONZE_PREFIX = Variable.get("taxi_s3_bronze_prefix", default_var="bronze/taxi")

# Iceberg Configuration
ICEBERG_CATALOG = Variable.get("iceberg_catalog", default_var="nycatalog")
SILVER_TABLE = f"{ICEBERG_CATALOG}.silver.yellow_taxi"
GOLD_TABLE = f"{ICEBERG_CATALOG}.gold.yellow_taxi"
AGG_TABLE = f"{ICEBERG_CATALOG}.agg.yellow_taxi"

# Taxi Zone Lookup
TAXI_ZONE_CSV = Variable.get(
    "taxi_zone_csv_path", default_var="s3://taxi-data-bucket/lookup/taxi-zones.csv"
)

# Spark Job Paths
TAXI_DOWNLOAD_SCRIPT = Variable.get(
    "taxi_download_script",
    default_var="/opt/airflow/jobs/taxi-download/download_with_partition.py",
)
CLEAN_SCRIPT = Variable.get(
    "clean_script", default_var="/opt/airflow/jobs/job/clean.py"
)
LOAD_SCRIPT = Variable.get("load_script", default_var="/opt/airflow/jobs/job/load.py")
AGG_SCRIPT = Variable.get(
    "agg_script", default_var="/opt/airflow/jobs/job/agg_table.py"
)

# ============================================================================
# Task Functions
# ============================================================================


def log_pipeline_config(**context):
    """Log configuration details for debugging."""
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"Raw Prefix: {S3_RAW_PREFIX}")
    print(f"Bronze Prefix: {S3_BRONZE_PREFIX}")
    print(f"Silver Table: {SILVER_TABLE}")
    print(f"Gold Table: {GOLD_TABLE}")
    print(f"Agg Table: {AGG_TABLE}")
    print(f"Taxi Zone CSV: {TAXI_ZONE_CSV}")


# ============================================================================
# DAG Tasks
# ============================================================================

# Start task
start = PythonOperator(
    task_id="start",
    python_callable=log_pipeline_config,
    dag=dag,
)

# ============================================================================
# Ingest Task Group
# ============================================================================

with TaskGroup("ingest", dag=dag) as ingest_group:

    download_taxi_data = BashOperator(
        task_id="download_taxi_data",
        bash_command=f"""
            python {TAXI_DOWNLOAD_SCRIPT} \
                --bucket {S3_BUCKET} \
                --prefix {S3_RAW_PREFIX}
        """,
        env={
            {
                "AWS_DEFAULT_REGION": "us-east-1",
            }
        },
    )

# ============================================================================
# Transformation Task Group
# ============================================================================

with TaskGroup("transformation", dag=dag) as transform_group:

    # Task: Clean & Validate (Bronze → Silver)
    clean_data = BashOperator(
        task_id="clean_data",
        bash_command=f"""
            spark-submit \
                --master yarn \
                --deploy-mode cluster \
                --num-executors 4 \
                --executor-cores 2 \
                --executor-memory 2g \
                --driver-memory 1g \
                {CLEAN_SCRIPT} \
                --bronze-path s3a://{S3_BUCKET}/{S3_BRONZE_PREFIX} \
                --silver_full_ref {SILVER_TABLE} \
                --incremental-col tpep_pickup_datetime
        """,
        env={
            {
                "AWS_DEFAULT_REGION": "us-east-1",
            }
        },
    )

    # Task: Load (Silver → Gold with enrichment)
    load_data = BashOperator(
        task_id="load_data",
        bash_command=f"""
            spark-submit \
                --master yarn \
                --deploy-mode cluster \
                --num-executors 4 \
                --executor-cores 2 \
                --executor-memory 2g \
                --driver-memory 1g \
                {LOAD_SCRIPT} \
                --silver_full_ref {SILVER_TABLE} \
                --gold_full_ref {GOLD_TABLE} \
                --s3_taxi_zone_csv {TAXI_ZONE_CSV}
        """,
        env={
            {
                "AWS_DEFAULT_REGION": "us-east-1",
            }
        },
    )

    # Task: Aggregate (Gold → Agg)
    aggregate_data = BashOperator(
        task_id="aggregate_data",
        bash_command=f"""
            spark-submit \
                --master yarn \
                --deploy-mode cluster \
                --num-executors 2 \
                --executor-cores 2 \
                --executor-memory 2g \
                --driver-memory 1g \
                {AGG_SCRIPT} \
                --gold_full_ref {GOLD_TABLE} \
                --agg_full_ref {AGG_TABLE}
        """,
        env={
            {
                "AWS_DEFAULT_REGION": "us-east-1",
            }
        },
    )

    # Set task dependencies within transformation group
    clean_data >> load_data >> aggregate_data

# ============================================================================
# Data Quality Check (Optional)
# ============================================================================

check_gold_table = BashOperator(
    task_id="check_gold_table",
    bash_command=f"""
        spark-sql -e "SELECT COUNT(*) AS total_rows FROM {GOLD_TABLE};"
    """,
    env={
        {
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    },
)

# ============================================================================
# End Task
# ============================================================================

end = PythonOperator(
    task_id="end",
    python_callable=lambda: print("ETL Pipeline completed successfully!"),
    dag=dag,
)

# ============================================================================
# DAG Dependencies
# ============================================================================

start >> ingest_group >> transform_group >> check_gold_table >> end
