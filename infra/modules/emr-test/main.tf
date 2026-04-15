resource "aws_emrserverless_application" "this" {
    name          = var.app_name
    release_label = var.release_label
    type          = "spark"

    maximum_capacity {
        cpu    = "10 vCPU"
        memory = "800 GB"
        disk   = "2000 GB"
    }

    initial_capacity {
        initial_capacity_type = "Driver"
        initial_capacity_config {
        worker_count = 1
        worker_configuration {
            cpu    = "1 vCPU"
            memory = "4 GB"
            }
        }
    }

    auto_start_configuration {
        enabled = true
    }

    auto_stop_configuration {
        enabled              = true
        idle_timeout_minutes = 15 # Tự động tắt sau 15 phút không có job nào chạy
    }

    runtime_configuration {
        classification = "spark-defaults"
        properties = {
            "spark.hadoop.hive.metastore.client.factory.class" = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"

            "spark.sql.extensions" = "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
            "spark.sql.catalog.glue_catalog"              = "org.apache.iceberg.spark.SparkCatalog"
            "spark.sql.catalog.glue_catalog.catalog-impl" = "org.apache.iceberg.aws.glue.GlueCatalog"
            "spark.sql.catalog.glue_catalog.io-impl"      = "org.apache.iceberg.aws.s3.S3FileIO"
            "spark.sql.catalog.glue_catalog.warehouse"    = "s3://${var.iceberg_warehouse_bucket_id}/"
        }
    }

    monitoring_configuration {
        cloudwatch_logging_configuration {
        enabled                = true
        log_group_name         = "/aws/emr-serverless/example"
        log_stream_name_prefix = "spark-logs"

        log_types {
            name   = "SPARK_DRIVER"
            values = ["STDOUT", "STDERR"]
        }

        log_types {
            name   = "SPARK_EXECUTOR"
            values = ["STDOUT"]
        }
        }

        managed_persistence_monitoring_configuration {
        enabled = true
        }

    }
}