resource "aws_glue_catalog_database" "nyc_taxi" {
  name = "nyc_taxi"
}

# resource "aws_glue_catalog_table" "iceberg_table" {
#   name          = "raw-yellow_taxi" # Tên bảng của bạn
#   database_name = aws_glue_catalog_database.nyc_taxi.name

#   table_type = "EXTERNAL_TABLE"

#   parameters = {
#     "table_type"                      = "ICEBERG"
#     "format"                          = "parquet"
    
#     # 1. Cấu hình Compaction (Tối ưu hóa file)
#     "write.format.default"            = "parquet"
#     "write.metadata.compression-codec"= "gzip"
    
#     # 2. Cấu hình Snapshot Retention (Dọn dẹp snapshot)
#     # Tương đương với giao diện UI bạn vừa xem
#     "history.expire.max-snapshot-age-ms" = "432000000" # 5 ngày (tính bằng milliseconds)
#     "history.expire.min-snapshots-to-keep" = "1"
    
#     # 3. Các cấu hình bổ sung khác
#     "parquet.compression"             = "snappy"
#   }

#   storage_descriptor {
#     location      = "s3://${var.iceberg_warehouse_bucket_id}/raw-yellow-taxi/"
#     input_format  = "org.apache.iceberg.mr.hive.HiveIcebergInputFormat"
#     output_format = "org.apache.iceberg.mr.hive.HiveIcebergOutputFormat"

#     ser_de_info {
#       serialization_library = "org.apache.iceberg.mr.hive.HiveIcebergSerDe"
#     }
#   }
# }

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