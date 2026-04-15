data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_s3_bucket" "iceberg-warehouse" {
  bucket        = format("iceberg-warehouse-%s-%s-an", data.aws_caller_identity.current.account_id, data.aws_region.current.name)
  force_destroy = true 
  bucket_namespace = "account-regional"
}

resource "aws_s3_bucket" "script-bucket" {
  bucket        = format("script-bucket-%s-%s-an", data.aws_caller_identity.current.account_id, data.aws_region.current.name)
  force_destroy = true
  bucket_namespace = "account-regional"
}