# 1. Tạo IAM User
resource "aws_iam_user" "athena_user" {
  name = "athena-powerbi-user"
  path = "/system/"
}

# 2. Tạo Access Key (để lấy Credentials cho Power BI)
resource "aws_iam_access_key" "athena_user_key" {
  user = aws_iam_user.athena_user.name
}

# 3. Định nghĩa Policy cho phép truy cập Athena, Glue và S3
resource "aws_iam_policy" "athena_access_policy" {
  name        = "AthenaQueryAccessPolicy"
  description = "Cho phép Power BI truy vấn Athena và đọc dữ liệu từ S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Quyền sử dụng Athena
        Action = [
          "athena:Get*",
          "athena:List*",
          "athena:StartQueryExecution",
          "athena:StopQueryExecution",
          "athena:BatchGetQueryExecution",
          "athena:GetQueryResultsStream"
        ],
        Effect   = "Allow"
        Resource = "*"
      },
      {
        # Quyền đọc Metadata từ Glue Data Catalog
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions"
        ],
        Effect   = "Allow"
        Resource = "*"
      },
      {
        # Quyền ghi kết quả truy vấn vào S3 Staging
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ],
        Effect   = "Allow"
        Resource = [
          var.warehouse_bucket_arn,
          "${var.warehouse_bucket_arn}/*"
        ]
      }
    ]
  })
}

# 4. Gắn Policy vào User
resource "aws_iam_user_policy_attachment" "athena_attach" {
  user       = aws_iam_user.athena_user.name
  policy_arn = aws_iam_policy.athena_access_policy.arn
}


