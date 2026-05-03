resource "aws_mwaa_environment" "myairflow" {
    name = "my-airflow-environment"
    airflow_version = "3.0.6"
    source_bucket_arn = var.script_bucket_arn
    dag_s3_path = "airflow/dags/"
    execution_role_arn = aws_iam_role.mwaa_execution_role.arn

    network_configuration {
        security_group_ids = var.security_group
        subnet_ids = var.private_subnets
    }

    webserver_access_mode = "PUBLIC_ONLY"
    environment_class = "mw1.micro"

    logging_configuration {
        dag_processing_logs {
        enabled   = true
        log_level = "DEBUG"
        }

        scheduler_logs {
        enabled   = true
        log_level = "INFO"
        }

        task_logs {
        enabled   = true
        log_level = "WARNING"
        }

        webserver_logs {
        enabled   = true
        log_level = "ERROR"
        }

        worker_logs {
        enabled   = true
        log_level = "CRITICAL"
        }
    }

}