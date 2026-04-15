# # Security Groups
# resource "aws_security_group" "workspace_sg" {
#   name   = "emr-studio-workspace-sg"
#   vpc_id = var.vpc_id
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

# resource "aws_security_group" "engine_sg" {
#   name   = "emr-studio-engine-sg"
#   vpc_id = var.vpc_id
#   ingress {
#     from_port       = 0
#     to_port         = 0
#     protocol        = "-1"
#     security_groups = [aws_security_group.workspace_sg.id]
#   }
# }

# # EMR Studio Resource
# resource "aws_emr_studio" "this" {
#   name                          = var.app_name
#   auth_mode                     = "IAM"
#   vpc_id                        = var.vpc_id
#   subnet_ids                    = var.public_subnet_ids
#   service_role                  = aws_iam_role.emr_studio_service_role.arn
#   workspace_security_group_id   = aws_security_group.workspace_sg.id
#   engine_security_group_id      = aws_security_group.engine_sg.id
#   default_s3_location           = "s3://${var.script_bucket_id}/workspaces"
# }

resource "aws_emrserverless_application" "this" {
    name          = var.app_name
    release_label = var.release_label
    type          = "spark"

    maximum_capacity {
        cpu    = "20 vCPU"
        memory = "80 GB"
        disk   = "100 GB"
    }

    # Bỏ initial_capacity để không tốn tiền chờ (Cold start sẽ chậm hơn một chút)

    auto_start_configuration {
        enabled = true
    }

    auto_stop_configuration {
        enabled              = true
        idle_timeout_minutes = 10 
    }

    runtime_configuration {
        classification = "spark-defaults"
        properties = {
            # Glue & Iceberg
            "spark.hadoop.hive.metastore.client.factory.class" = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
            "spark.sql.extensions" = "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
            "spark.sql.catalog.glue_catalog"               = "org.apache.iceberg.spark.SparkCatalog"
            "spark.sql.catalog.glue_catalog.catalog-impl"  = "org.apache.iceberg.aws.glue.GlueCatalog"
            "spark.sql.catalog.glue_catalog.io-impl"       = "org.apache.iceberg.aws.s3.S3FileIO"
            "spark.sql.catalog.glue_catalog.warehouse"     = "s3://${var.iceberg_warehouse_bucket_id}/"

            # Resource Saving
            "spark.driver.cores"                   = "1"
            "spark.driver.memory"                  = "2g"
            "spark.executor.cores"                 = "1"
            "spark.executor.memory"                = "2g"
            "spark.dynamicAllocation.maxExecutors" = "2"
        }
    }

    interactive_configuration {
        studio_enabled = true
    }
}