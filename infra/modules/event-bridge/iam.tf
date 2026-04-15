# Trust Policy cho EventBridge
resource "aws_iam_role" "event_bridge_scheduler_role" {
  name = "nyc-taxi-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

# Policy cho phép Submit Job
resource "aws_iam_role_policy" "event_bridge_batch_policy" {
  name = "AllowSubmitBatchJob"
  role = aws_iam_role.event_bridge_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "batch:SubmitJob"
        Effect = "Allow"
        Resource = "*" # Bạn có thể giới hạn ARN của Job Queue và Job Definition cụ thể
      }
    ]
  })
}