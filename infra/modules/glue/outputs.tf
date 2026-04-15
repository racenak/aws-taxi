output "aws_glue_catalog_database_name" {
  value = aws_glue_catalog_database.nyc_taxi.name
}

output "glue_crawler_role_arn" {
  value = aws_iam_role.glue_crawler_role.arn
}