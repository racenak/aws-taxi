resource "aws_iam_role" "glue_crawler_role" {
  name = "GlueCrawlerRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "s3_access" {
  name = "GlueS3Access"
  role = aws_iam_role.glue_crawler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # 1. Quyền trên chính Bucket (để List file)
        Action   = ["s3:ListBucket"]
        Effect   = "Allow"
        Resource = [
          var.iceberg_warehouse_bucket_arn
        ]
      },
      {
        # 2. Quyền trên các Object bên trong (để đọc/ghi dữ liệu)
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = [
          "${var.iceberg_warehouse_bucket_arn}/*"
        ]
      }
    ]
  })
}