output "raw_bucket_arn" {
  description = "ARN của bucket chứa dữ liệu thô"
  value       = aws_s3_bucket.raw.arn
}

output "cleaned_bucket_arn" {
  description = "ARN của bucket chứa dữ liệu đã xử lý"
  value       = aws_s3_bucket.cleaned.arn
}

output "raw_bucket_id" {
  description = "Tên (ID) của bucket raw"
  value       = aws_s3_bucket.raw.id
}

output "cleaned_bucket_id" {
  description = "Tên (ID) của bucket cleaned"
  value       = aws_s3_bucket.cleaned.id
}