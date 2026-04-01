data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_s3_bucket" "raw" {
  bucket        = format("raw-yellow-taxi-%s-%s-an", data.aws_caller_identity.current.account_id, data.aws_region.current.name)
  force_destroy = true 
}

resource "aws_s3_bucket" "cleaned" {
  bucket        = format("cleaned-yellow-taxi-%s-%s-an", data.aws_caller_identity.current.account_id, data.aws_region.current.name)
  force_destroy = true
}