resource "aws_iam_role" "mwaa_execution_role" {
  name = "aws-mwaa-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "airflow.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "mwaa_cloudwatch_policy" {
  name   = "mwaa-cloudwatch-policy"
  role   = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:GetLogRecord",
          "logs:GetQueryResults",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/airflow/*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "mwaa_s3_policy" {
  name   = "mwaa-s3-policy"
  role   = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketVersioning"
        ]
        Resource = [
          "${var.script_bucket_arn}/airflow/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "mwaa_sqs_policy" {
  name   = "mwaa-sqs-policy"
  role   = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = "arn:aws:sqs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "mwaa_kms_policy" {
  name   = "mwaa-kms-policy"
  role   = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
}
