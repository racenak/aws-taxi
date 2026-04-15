resource "aws_scheduler_schedule" "taxi_ingest_monthly" {
  name        = "nyc-taxi-monthly-ingest"
  group_name  = "default"

  flexible_time_window {
    mode = "OFF"
  }

  # Chạy vào 00:00 ngày 1 hàng tháng
  schedule_expression = "cron(0 0 1 * ? *)"
  schedule_expression_timezone = "Asia/Ho_Chi_Minh" # Bạn có thể chỉnh múi giờ Việt Nam

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:batch:submitJob"
    role_arn = aws_iam_role.event_bridge_scheduler_role.arn

    input = jsonencode({
      JobDefinition = var.batch_job_definition_arn
      JobName       = "MonthlyIngestTaxiData"
      JobQueue      = var.batch_job_queue_arn
      
      # Ghi đè tham số (Ref::) trong Job Definition
      Parameters = {
        start_year = "2026"
        end_year   = "2026"
        s3_bucket  = var.target_s3_bucket_name
      }
    })
  }
}