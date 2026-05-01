from __future__ import annotations

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.batch import BatchOperator
from airflow.providers.amazon.aws.sensors.batch import BatchSensor

# ---------------------------------------------------------------------------
# Default args
# ---------------------------------------------------------------------------
default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
}

# ---------------------------------------------------------------------------
# Constants — override via Airflow Variables in production
# ---------------------------------------------------------------------------
S3_BUCKET      = Variable.get("nyc_taxi_s3_bucket",  default_var="my-data-lake")
S3_PREFIX      = Variable.get("nyc_taxi_s3_prefix",  default_var="raw/taxi")
BATCH_JOB_QUEUE = Variable.get("batch_job_queue",    default_var="data-pipeline-queue")
BATCH_JOB_DEF   = Variable.get("batch_job_def",      default_var="nyc-taxi-downloader:latest")

# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------

def build_batch_overrides(target_year: int | None, bucket: str, prefix: str) -> dict:
    """Build AWS Batch container overrides from DAG params."""
    command = ["--bucket", bucket, "--prefix", prefix]
    if target_year:
        command += ["--year", str(target_year)]
    return {
        "command": command,
        "environment": [
            {"name": "AWS_DEFAULT_REGION", "value": "ap-southeast-1"},
        ],
    }


def prepare_download_task(
    ti,
    target_year: int | None,
    bucket: str,
    prefix: str,
    **context,
) -> None:
    """
    Pre-flight task: validate params and push a manifest to XCom
    so downstream tasks know what to expect.
    """
    execution_date: datetime = context["execution_date"]

    # Decide which months will be downloaded
    if target_year:
        months = list(range(1, 13))
        data_year = target_year
    else:
        # Previous month (same logic as the script)
        prev = (execution_date.replace(day=1) - timedelta(days=1))
        data_year = prev.year
        months = [prev.month]

    expected_files = [
        {
            "year": data_year,
            "month": month,
            "s3_uri": (
                f"s3://{bucket}/{prefix}/"
                f"year={execution_date.year}/"
                f"yellow_tripdata_{data_year}-{month:02d}.parquet"
            ),
        }
        for month in months
    ]

    # ── Push to XCom so every downstream task can read it ──────────────────
    ti.xcom_push(key="expected_files",       value=expected_files)
    ti.xcom_push(key="download_s3_bucket",   value=bucket)
    ti.xcom_push(key="download_s3_prefix",   value=prefix)
    ti.xcom_push(key="data_year",            value=data_year)
    ti.xcom_push(key="data_months",          value=months)
    ti.xcom_push(key="execution_date_iso",   value=execution_date.isoformat())

    print(f"[prepare] Manifest pushed to XCom: {json.dumps(expected_files, indent=2)}")


def verify_download_results(ti, **context) -> None:
    """
    Post-download task: pull Batch job results (written to S3 by the job
    as a JSON report) and validate against the manifest.

    Convention: the Batch job writes a JSON report to
        s3://{bucket}/{prefix}/reports/year={year}/{run_id}.json
    This task reads it via boto3 and pushes a verified manifest forward.
    """
    import boto3

    expected_files: list[dict] = ti.xcom_pull(
        task_ids="prepare_download", key="expected_files"
    )
    bucket: str = ti.xcom_pull(task_ids="prepare_download", key="download_s3_bucket")
    prefix: str = ti.xcom_pull(task_ids="prepare_download", key="download_s3_prefix")
    data_year: int = ti.xcom_pull(task_ids="prepare_download", key="data_year")

    # Pull Batch report written by the container
    run_id = context["run_id"].replace(":", "_").replace("+", "_")
    report_key = f"{prefix}/reports/year={data_year}/{run_id}.json"

    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=report_key)
        batch_results: dict = json.loads(obj["Body"].read())
        print(f"[verify] Batch report: {json.dumps(batch_results, indent=2)}")
    except s3.exceptions.NoSuchKey:
        # Batch job didn't write a report – fall back to head_object checks
        print("[verify] No report found; falling back to S3 head_object checks.")
        batch_results = {"results": []}

    # Cross-check
    successful_uris = {
        r["s3_uri"]
        for r in batch_results.get("results", [])
        if r.get("status") in ("success", "skipped")
    }

    verified, failed = [], []
    for f in expected_files:
        if f["s3_uri"] in successful_uris:
            verified.append(f)
        else:
            # Still try head_object as last resort
            key = f["s3_uri"].replace(f"s3://{bucket}/", "")
            try:
                s3.head_object(Bucket=bucket, Key=key)
                verified.append(f)
            except Exception:
                failed.append(f)

    if failed:
        raise ValueError(f"[verify] {len(failed)} file(s) missing after download: {failed}")

    # ── Push verified manifest for downstream tasks ─────────────────────────
    ti.xcom_push(key="verified_files", value=verified)
    ti.xcom_push(key="verified_count", value=len(verified))
    print(f"[verify] {len(verified)} file(s) verified OK.")


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="nyc_yellow_taxi_pipeline",
    description="Download NYC Yellow Taxi data → S3 via AWS Batch",
    schedule_interval="0 6 1 * *",       # 06:00 on the 1st of every month
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["nyc-taxi", "aws-batch", "ingestion"],
    params={
        "target_year": None,             # Pass an int to backfill a full year
        "s3_bucket":   S3_BUCKET,
        "s3_prefix":   S3_PREFIX,
    },
    doc_md="""
## NYC Yellow Taxi Pipeline

**Flow:**
`prepare_download` → `submit_batch_job` → `wait_for_batch_job` → `verify_results` → *your tasks*

**Cross-task communication via XCom:**

| Key | Pushed by | Contains |
|-----|-----------|----------|
| `expected_files` | `prepare_download` | list of `{year, month, s3_uri}` |
| `download_s3_bucket` | `prepare_download` | bucket name |
| `data_year` | `prepare_download` | int |
| `verified_files` | `verify_results` | successfully downloaded files |
| `verified_count` | `verify_results` | int count |
""",
) as dag:

    # 1. ── Validate + build manifest ────────────────────────────────────────
    prepare_download = PythonOperator(
        task_id="prepare_download",
        python_callable=prepare_download_task,
        op_kwargs={
            "target_year": "{{ params.target_year }}",
            "bucket":      "{{ params.s3_bucket }}",
            "prefix":      "{{ params.s3_prefix }}",
        },
    )

    # 2. ── Submit the Batch job (runs your Python script) ───────────────────
    submit_batch_job = BatchOperator(
        task_id="submit_batch_job",
        job_name="nyc-taxi-download-{{ ds_nodash }}",
        job_definition=BATCH_JOB_DEF,
        job_queue=BATCH_JOB_QUEUE,
        overrides=build_batch_overrides(
            target_year=None,          # resolved at runtime via params
            bucket=S3_BUCKET,
            prefix=S3_PREFIX,
        ),
        # Pass run_id so the container can name its report file
        container_overrides={
            "environment": [
                {"name": "AIRFLOW_RUN_ID", "value": "{{ run_id }}"},
                {"name": "S3_BUCKET",      "value": "{{ params.s3_bucket }}"},
                {"name": "S3_PREFIX",      "value": "{{ params.s3_prefix }}"},
                {
                    "name": "TARGET_YEAR",
                    "value": "{{ params.target_year if params.target_year else '' }}",
                },
            ]
        },
        awslogs_group="/aws/batch/nyc-taxi",
        awslogs_stream_prefix="nyc-taxi-download",
        wait_for_completion=False,     # use the sensor below for visibility
    )

    # 3. ── Poll until job finishes ───────────────────────────────────────────
    wait_for_batch_job = BatchSensor(
        task_id="wait_for_batch_job",
        job_id="{{ task_instance.xcom_pull('submit_batch_job') }}",
        poke_interval=60,
        timeout=60 * 60 * 4,          # 4-hour max
        mode="reschedule",            # free the worker slot while waiting
    )

    # 4. ── Verify output & push verified manifest ────────────────────────────
    verify_results = PythonOperator(
        task_id="verify_results",
        python_callable=verify_download_results,
    )

    # ---------------------------------------------------------------------------
    # Example downstream tasks — replace with your real logic
    # ---------------------------------------------------------------------------

    def example_transform_task(ti, **_):
        """Downstream task that reads the verified manifest."""
        verified_files: list[dict] = ti.xcom_pull(
            task_ids="verify_results", key="verified_files"
        )
        print(f"Transforming {len(verified_files)} file(s):")
        for f in verified_files:
            print(f"  → {f['s3_uri']}")
        # ... your Spark / dbt / Glue logic here

    transform_data = PythonOperator(
        task_id="transform_data",
        python_callable=example_transform_task,
    )

    # ---------------------------------------------------------------------------
    # Pipeline wiring
    # ---------------------------------------------------------------------------
    prepare_download >> submit_batch_job >> wait_for_batch_job >> verify_results >> transform_data