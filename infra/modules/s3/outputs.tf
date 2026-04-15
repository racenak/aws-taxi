output "iceberg_warehouse_bucket_arn" {
  description = "ARN của bucket chứa dữ liệu thô"
  value       = aws_s3_bucket.iceberg-warehouse.arn
}

output "script_bucket_arn" {
  description = "ARN của bucket chứa dữ liệu đã xử lý"
  value       = aws_s3_bucket.script-bucket.arn
}

output "iceberg_warehouse_bucket_id" {
  description = "Tên (ID) của bucket iceberg-warehouse"
  value       = aws_s3_bucket.iceberg-warehouse.id
}

output "script_bucket_id" {
  description = "Tên (ID) của bucket script-bucket"
  value       = aws_s3_bucket.script-bucket.id
}