resource "aws_glue_catalog_database" "nyc_taxi" {
  name = "nyc_taxi"
}

resource "aws_glue_crawler" "nyc_taxi_crawler" {
  database_name = aws_glue_catalog_database.nyc_taxi.name
  name          = "crawler-raw-yellow-taxi"
  role          = aws_iam_role.glue_crawler_role.arn

  # Cấu hình nguồn dữ liệu (S3)
  s3_target {
    path = var.target_bucket_uri
  }


  # Cấu hình cách xử lý khi schema thay đổi
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}