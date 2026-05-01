"""
NYC Yellow Taxi ETL - Parameterized DAG with Backfill Support

This DAG allows running individual ETL stages with custom parameters.
Useful for backfilling specific months or re-running failed stages.

Usage:
    airflow dags trigger \
        --exec-date 2024-01-01 \
        taxi_etl_backfill \
        --conf '{"year": 2024, "month": 1, "stage": "all"}'
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable
import json

# ============================================================================
# Default Args
# ============================================================================

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ============================================================================
# DAG Definition
# ============================================================================

dag = DAG(
    "taxi_etl_backfill",
    default_args=default_args,
    description="NYC Yellow Taxi ETL Backfill - Run specific stage/month",
    schedule_interval=None,  # Triggered manually
    catchup=False,
    tags=["etl", "taxi", "backfill"],
)

# ============================================================================
# Configuration
# ============================================================================

S3_BUCKET = Variable.get("taxi_s3_bucket", default_var="taxi-data-bucket")
S3_RAW_PREFIX = Variable.get("taxi_s3_raw_prefix", default_var="raw/taxi")
ICEBERG_CATALOG = Variable.get("iceberg_catalog", default_var="nycatalog")
SILVER_TABLE = f"{ICEBERG_CATALOG}.silver.yellow_taxi"
GOLD_TABLE = f"{ICEBERG_CATALOG}.gold.yellow_taxi"
AGG_TABLE = f"{ICEBERG_CATALOG}.agg.yellow_taxi"
TAXI_ZONE_CSV = Variable.get(
    "taxi_zone_csv_path", default_var="s3://taxi-data-bucket/lookup/taxi-zones.csv"
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


def extract_dag_config(**context):
    """Extract and log configuration from DAG run params."""
    conf = context.get("dag_run").conf or {}

    year = conf.get("year", datetime.now().year)
    month = conf.get("month", datetime.now().month)
    stage = conf.get("stage", "all")  # all, ingest, clean, load, aggregate

    print(f"DAG Params - Year: {year}, Month: {month}, Stage: {stage}")

    # Store in XCom for other tasks
    context["task_instance"].xcom_push(key="year", value=year)
    context["task_instance"].xcom_push(key="month", value=month)
    context["task_instance"].xcom_push(key="stage", value=stage)

    return {"year": year, "month": month, "stage": stage}


# ============================================================================
# DAG Tasks
# ============================================================================

start = PythonOperator(
    task_id="extract_config",
    python_callable=extract_dag_config,
    provide_context=True,
    dag=dag,
)

# ============================================================================
# Ingest Stage
# ============================================================================

with TaskGroup("stage_ingest", dag=dag) as ingest_group:

    download_year = BashOperator(
        task_id="download_taxi_year",
        bash_command=f"""
            YEAR="{{{{ ti.xcom_pull(key='year') }}}}"
            python {Variable.get('taxi_download_script')} \
                --year "$YEAR" \
                --bucket {S3_BUCKET} \
                --prefix {S3_RAW_PREFIX}
        """,
    )

# ============================================================================
# Transformation Stage
# ============================================================================

with TaskGroup("stage_transformation", dag=dag) as transformation_group:

    clean_task = BashOperator(
        task_id="clean_data",
        bash_command=f"""
            spark-submit \
                --master yarn \
                --deploy-mode cluster \
                --num-executors 4 \
                --executor-cores 2 \
                --executor-memory 2g \
                {CLEAN_SCRIPT} \
                --bronze-path s3a://{S3_BUCKET}/{S3_RAW_PREFIX} \
                --silver_full_ref {SILVER_TABLE}
        """,
    )

    load_task = BashOperator(
        task_id="load_data",
        bash_command=f"""
            spark-submit \
                --master yarn \
                --deploy-mode cluster \
                --num-executors 4 \
                --executor-cores 2 \
                --executor-memory 2g \
                {LOAD_SCRIPT} \
                --silver_full_ref {SILVER_TABLE} \
                --gold_full_ref {GOLD_TABLE} \
                --s3_taxi_zone_csv {TAXI_ZONE_CSV}
        """,
    )

    agg_task = BashOperator(
        task_id="aggregate_data",
        bash_command=f"""
            spark-submit \
                --master yarn \
                --deploy-mode cluster \
                --num-executors 2 \
                --executor-cores 2 \
                --executor-memory 2g \
                {AGG_SCRIPT} \
                --gold_full_ref {GOLD_TABLE} \
                --agg_full_ref {AGG_TABLE}
        """,
    )

    clean_task >> load_task >> agg_task

# ============================================================================
# Validation Stage
# ============================================================================

validate_tables = BashOperator(
    task_id="validate_tables",
    bash_command=f"""
        echo "=== Validation Results ==="
        echo "Silver Row Count:"
        spark-sql -e "SELECT COUNT(*) FROM {SILVER_TABLE};"

        echo "Gold Row Count:"
        spark-sql -e "SELECT COUNT(*) FROM {GOLD_TABLE};"

        echo "Agg Row Count:"
        spark-sql -e "SELECT COUNT(*) FROM {AGG_TABLE};"
    """,
    dag=dag,
)

end = PythonOperator(
    task_id="end",
    python_callable=lambda: print("Backfill ETL completed!"),
    dag=dag,
)

# ============================================================================
# DAG Dependencies
# ============================================================================

start >> ingest_group >> transformation_group >> validate_tables >> end
