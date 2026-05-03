from __future__ import annotations

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.providers.amazon.aws.operators.batch import BatchOperator
from airflow.providers.amazon.aws.operators.emr import EmrServerlessStartJobOperator

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

BATCH_JOB_DEF = "nyc-taxi-job-definition"
BATCH_JOB_QUEUE = "nyc-taxi-queue"

EMR_SERVERLESS_APPLICATION_ID = Variable.get("emr_serverless_application_id")
EMR_EXECUTION_ROLE_ARN = Variable.get("emr_execution_role_arn")
SCRIPT_BUCKET = Variable.get("s3_script_bucket")
BRONZE_PATH = Variable.get("full_bronze_path")

S3_FULL_TAXI_ZONE_CSV = Variable.get("full_taxi_zone_csv")

with DAG(
    dag_id="nyc_yellow_taxi_pipeline",
    schedule="0 6 1 * *",       # 06:00 on the 1st of every month
    catchup=False,
    default_args=default_args
) as dag:
    submit_batch_job = BatchOperator(
        task_id="submit_batch_job",
        job_name="nyc-taxi-download-{{ ds_nodash }}",
        job_definition=BATCH_JOB_DEF,
        job_queue=BATCH_JOB_QUEUE,
        container_overrides = {
            "command": [
                "python",
                "download_with_partition.py",
                "--target_year", "2026",
                "--bucket", Variable.get("s3_bucket"),
                "--prefix", Variable.get("s3_prefix", default_var="raw/raw-yellow-taxi/")
            ],
            "environment": [
                {"name": "AIRFLOW_RUN_ID", "value": "{{ run_id }}"}
            ]
        },
        awslogs_enabled=True
    )

    clean_data = EmrServerlessStartJobOperator(
        application_id=EMR_SERVERLESS_APPLICATION_ID,
        execution_role_arn=EMR_EXECUTION_ROLE_ARN,
        job_driver={
            "sparkSubmit": {
                "entryPoint": f"s3://{SCRIPT_BUCKET}/sparkjobs/clean.py",
                "entryPointArguments": [
                    "--bronze-path", BRONZE_PATH,
                    "--silver_full_ref", "glue_catalog.nyc_taxi.silver_yellow_taxi",
                ]
            }
        }
    )

    load_to_gold = EmrServerlessStartJobOperator(
        application_id=EMR_SERVERLESS_APPLICATION_ID,
        execution_role_arn=EMR_EXECUTION_ROLE_ARN,
        job_driver={
            "sparkSubmit": {
                "entryPoint": f"s3://{SCRIPT_BUCKET}/sparkjobs/load.py",
                "entryPointArguments": [
                    "--silver_full_ref", "glue_catalog.nyc_taxi.silver_yellow_taxi",
                    "--gold_full_ref", "glue_catalog.nyc_taxi.gold_yellow_taxi",
                    "--s3_taxi_zone_csv", S3_FULL_TAXI_ZONE_CSV
                ]
            }
        }
    )

    agg_table = EmrServerlessStartJobOperator(
        application_id=EMR_SERVERLESS_APPLICATION_ID,
        execution_role_arn=EMR_EXECUTION_ROLE_ARN,
        job_driver={
            "sparkSubmit": {
                "entryPoint": f"s3://{SCRIPT_BUCKET}/sparkjobs/agg_table.py",
                "entryPointArguments": [
                    "--gold_full_ref", "glue_catalog.nyc_taxi.gold_yellow_taxi",
                    "--agg_full_ref", "glue_catalog.nyc_taxi.agg_yellow_taxi"
                ]
            }
        }
    )

    submit_batch_job >> clean_data >> load_to_gold >> agg_table