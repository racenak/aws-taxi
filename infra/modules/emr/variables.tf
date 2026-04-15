variable "app_name" {
  default = "data-engineer-studio"
}

# variable "vpc_id" {
#   description = "VPC ID để triển khai EMR Studio"
# }

# variable "public_subnet_ids" {
#   type        = list(string)
#   description = "Danh sách Subnet IDs (Nên dùng Private Subnet có NAT Gateway)"
# }

variable "iceberg_warehouse_bucket_arn" {
  description = "ARN của S3 Bucket chứa dữ liệu Iceberg"
}

variable "script_bucket_arn" {
  description = "ARN của S3 Bucket chứa script và logs"
}

# variable "script_bucket_id" {
#   description = "ID của S3 Bucket chứa script và logs"
# }

variable "release_label" {
  description = "Phiên bản EMR (ví dụ: emr-6.6.0)"
  type        = string
  default     = "emr-7.12.0"
}

variable "iceberg_warehouse_bucket_id" {
  description = "ID của S3 bucket mà EMR sẽ truy cập để đọc/ghi dữ liệu"
  type        = string
}