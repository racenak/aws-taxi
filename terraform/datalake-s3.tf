# variable "datalake_bucket_names" {
#   type    = list(string)
#   default = ["raw-data", "processed-data"]
# }

# resource "aws_s3_bucket" "datalake" {
#   for_each = toset(var.datalake_bucket_names)

#   bucket = "${each.value}" 

# }

# resource "aws_s3_bucket_versioning" "versioning" {
#   for_each = aws_s3_bucket.datalake

#   bucket = each.value.id
#   versioning_configuration {
#     status = "Enabled"
#   }
# }

# resource "aws_s3_bucket_public_access_block" "block_public" {
#   for_each = aws_s3_bucket.datalake

#   bucket = each.value.id

#   block_public_acls       = true
#   block_public_policy     = true
#   ignore_public_acls      = true
#   restrict_public_buckets = true
# }