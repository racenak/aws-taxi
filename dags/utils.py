"""
Utility functions and helpers for Taxi ETL DAGs
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Date Helpers
# ============================================================================


def get_previous_month() -> tuple:
    """Return (year, month) for the previous month."""
    today = datetime.today()
    first_day = today.replace(day=1)
    last_day_prev = first_day - timedelta(days=1)
    return last_day_prev.year, last_day_prev.month


def get_date_range(year: int, month: int) -> tuple:
    """
    Return (start_date, end_date) for a given year/month.
    Returns: (datetime, datetime)
    """
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    return start, end


# ============================================================================
# Spark Helpers
# ============================================================================


def build_spark_submit_command(
    script_path: str,
    master: str = "yarn",
    deploy_mode: str = "cluster",
    num_executors: int = 4,
    executor_cores: int = 2,
    executor_memory: str = "2g",
    driver_memory: str = "1g",
    additional_args: Dict[str, str] = None,
    additional_configs: Dict[str, str] = None,
) -> str:
    """
    Build a spark-submit command with standard parameters.

    Args:
        script_path: Path to the PySpark script
        master: Spark master URL
        deploy_mode: "cluster" or "client"
        num_executors: Number of executors
        executor_cores: Cores per executor
        executor_memory: Memory per executor
        driver_memory: Driver memory
        additional_args: Dict of CLI args for the script (--key value)
        additional_configs: Dict of Spark configs (--conf key=value)

    Returns:
        Complete spark-submit command string
    """
    cmd = [
        "spark-submit",
        f"--master {master}",
        f"--deploy-mode {deploy_mode}",
        f"--num-executors {num_executors}",
        f"--executor-cores {executor_cores}",
        f"--executor-memory {executor_memory}",
        f"--driver-memory {driver_memory}",
    ]

    # Add Spark configurations
    if additional_configs:
        for key, value in additional_configs.items():
            cmd.append(f"--conf {key}={value}")

    # Add script path
    cmd.append(script_path)

    # Add script arguments
    if additional_args:
        for key, value in additional_args.items():
            cmd.append(f"--{key} {value}")

    return " ".join(cmd)


# ============================================================================
# Task Output Handlers
# ============================================================================


def parse_spark_submit_output(output: str) -> Dict[str, Any]:
    """
    Parse spark-submit logs for success/failure and key metrics.

    Args:
        output: Full spark-submit output

    Returns:
        Dict with status and metrics
    """
    result = {
        "success": False,
        "rows_processed": 0,
        "duration_seconds": 0,
        "error": None,
    }

    # Check for success indicators
    if "successfully" in output.lower() or "completed" in output.lower():
        result["success"] = True

    # Check for common errors
    if "exception" in output.lower() or "error" in output.lower():
        result["success"] = False
        # Extract error message (simplified)
        for line in output.split("\n"):
            if "error" in line.lower():
                result["error"] = line.strip()
                break

    logger.info(f"Spark job result: {result}")
    return result


# ============================================================================
# Validation Helpers
# ============================================================================


def validate_table_reference(table_ref: str) -> bool:
    """
    Validate Iceberg table reference format: catalog.schema.table

    Args:
        table_ref: Table reference string

    Returns:
        True if valid, raises ValueError otherwise
    """
    parts = table_ref.split(".")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid table reference '{table_ref}'. "
            "Expected format: <catalog>.<schema>.<table>"
        )
    return True


def validate_s3_path(s3_path: str) -> bool:
    """
    Validate S3 path format: s3://bucket/prefix

    Args:
        s3_path: S3 path string

    Returns:
        True if valid, raises ValueError otherwise
    """
    if not s3_path.startswith("s3://") and not s3_path.startswith("s3a://"):
        raise ValueError(
            f"Invalid S3 path '{s3_path}'. "
            "Expected format: s3://bucket/prefix or s3a://bucket/prefix"
        )
    return True


# ============================================================================
# Notification Helpers
# ============================================================================


def send_completion_notification(
    dag_id: str,
    task_id: str,
    status: str,
    context: Dict[str, Any],
) -> None:
    """
    Send notification on task completion (e.g., Slack, email).

    Args:
        dag_id: DAG identifier
        task_id: Task identifier
        status: "success" or "failure"
        context: Airflow task context
    """
    execution_date = context["execution_date"]
    try_number = context["task_instance"].try_number

    message = (
        f"DAG: {dag_id}\n"
        f"Task: {task_id}\n"
        f"Status: {status}\n"
        f"Execution Date: {execution_date}\n"
        f"Try Number: {try_number}"
    )

    logger.info(f"Notification: {message}")
    # TODO: Integrate with Slack or email service
    # slack_client.post_message(channel="#alerts", text=message)


# ============================================================================
# Logging Helpers
# ============================================================================


def setup_logging(task_id: str, dag_id: str) -> logging.Logger:
    """
    Set up logging for a task.

    Args:
        task_id: Task identifier
        dag_id: DAG identifier

    Returns:
        Configured logger
    """
    logger_name = f"{dag_id}.{task_id}"
    logger_obj = logging.getLogger(logger_name)
    logger_obj.setLevel(logging.INFO)

    if not logger_obj.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger_obj.addHandler(handler)

    return logger_obj
