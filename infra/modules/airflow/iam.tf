resource "aws_iam_role" "mwaa_execution_role" {
  name = "aws-mwaa-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["airflow-env.amazonaws.com", "airflow.amazonaws.com"]
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "mwaa_execution_policy" {
  name   = "mwaa-execution-policy"
  role   = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "airflow:PublishMetrics"
        Resource = "arn:aws:airflow:ap-southeast-1::environment/MyAirflowEnvironment"
      },
      {
        Effect = "Deny"
        Action = "s3:ListAllMyBuckets"
        Resource = [
          var.script_bucket_arn,
          "${var.script_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject*",
          "s3:GetBucket*",
          "s3:List*"
        ]
        Resource = [
          var.script_bucket_arn,
          "${var.script_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:GetLogRecord",
          "logs:GetLogGroupFields",
          "logs:GetQueryResults"
        ]
        Resource = [
          "arn:aws:logs:ap-southeast-1::log-group:airflow-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups"
        ]
        Resource = [
          "*"
        ]
      },
      {
        Effect = "Allow"
        Action = "cloudwatch:PutMetricData"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ChangeMessageVisibility",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ReceiveMessage",
          "sqs:SendMessage"
        ]
        Resource = "arn:aws:sqs:ap-southeast-1::*:airflow-celery-*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey*",
          "kms:Encrypt"
        ]
        NotResource = "arn:aws:kms:*::key/*"
        Condition = {
          StringLike = {
            "kms:ViaService" = [
              "sqs.ap-southeast-1.amazonaws.com"
            ]
          }
        }
      }
    ]
  })
}


resource "aws_iam_role_policy" "mwaa_execution_batch_policy" {
  name  = "mwaa-execution-batch-policy"
  role   = aws_iam_role.mwaa_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
    {
      "Effect": "Allow",
      "Action": [
        "batch:SubmitJob",
        "batch:DescribeJobs",
        "batch:TerminateJob",
        "batch:ListJobs"
      ],
      "Resource": [
        "${var.batch_job_queue_arn}/*",
        "${var.batch_job_definition_arn}/*"
      ]
    }
    ]
  })
}