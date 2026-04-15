data "aws_iam_policy_document" "emr_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["emr-serverless.amazonaws.com"]
    }
  }
}


resource "aws_iam_role" "emr_serverless_role" {
  name               = "${var.app_name}-execution-role"
  assume_role_policy = data.aws_iam_policy_document.emr_assume_role.json
}


resource "aws_iam_policy" "emr_serverless_policy" {
  name        = "${var.app_name}-policy"
  description = "Quyen han cho EMR Serverless truy cap S3 va Logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:DeleteObject",]
        Effect   = "Allow"
        Resource = ["${var.iceberg_warehouse_bucket_arn}", 
                    "${var.iceberg_warehouse_bucket_arn}/*",
                    "${var.script_bucket_arn}",
                    "${var.script_bucket_arn}/*"
        ]
      },
      {
        Action   = ["logs:CreateLogGroup", 
                    "logs:CreateLogStream", 
                    "logs:PutLogEvents", 
                    "logs:DescribeLogGroups", 
                    "logs:DescribeLogStreams"]
        Effect   = "Allow"
        Resource = ["arn:aws:logs:*:*:*"]
      },
      {
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:CreateDatabase",
          "glue:CreateTable",
          "glue:GetTable",
          "glue:GetTables",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:CreatePartition",
          "glue:BatchCreatePartition",
          "glue:BatchGetPartition"
        ]
        Effect   = "Allow"
        Resource = ["*"]
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "emr_attach" {
  role       = aws_iam_role.emr_serverless_role.name
  policy_arn = aws_iam_policy.emr_serverless_policy.arn
}