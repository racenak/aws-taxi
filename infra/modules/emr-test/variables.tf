variable "app_name" {
  description = "Tên của EMR Serverless Application"
  type        = string
  default     = "my-emr-serverless-app"
}

variable "release_label" {
  description = "Phiên bản EMR (ví dụ: emr-6.6.0)"
  type        = string
  default     = "emr-7.12.0"
}

variable "iceberg_warehouse_bucket_id" {
  description = "ID của S3 bucket mà EMR sẽ truy cập để đọc/ghi dữ liệu"
  type        = string
}

variable "iceberg_warehouse_bucket_arn" {
  description = "ARN của S3 bucket mà EMR sẽ truy cập để đọc/ghi dữ liệu"
  type        = string
}

variable "script_bucket_arn" {
  description = "ARN của S3 bucket chứa các script mà EMR sẽ chạy"
  type        = string
}