# 1. Môi trường tính toán (Fargate)
resource "aws_batch_compute_environment" "fargate_env" {
  name = "${var.project_name}-fargate-env"

  compute_resources {
    type               = "FARGATE"
    max_vcpus          = 1
    security_group_ids = var.security_group_ids
    subnets            = var.subnet_ids
  }

  service_role = aws_iam_role.batch_service_role.arn
  type         = "MANAGED"
  state        = "ENABLED"
  
  depends_on = [aws_iam_role_policy_attachment.batch_service_attach]
}

# 2. Hàng đợi Job
resource "aws_batch_job_queue" "batch_queue" {
  name     = "${var.project_name}-queue"
  state    = "ENABLED"
  priority = 1
  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.fargate_env.arn
  }
}

# 3. Định nghĩa Job
resource "aws_batch_job_definition" "job_def" {
  name = "${var.project_name}-job-definition"
  type = "container"
  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image      = var.container_image
    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }
    resourceRequirements = [
      { type = "VCPU", value = "1" },
      { type = "MEMORY", value = "4096" }
    ]
    executionRoleArn = aws_iam_role.batch_execution_role.arn
    command          = ["echo", "AWS Batch is running!"]
  })
}