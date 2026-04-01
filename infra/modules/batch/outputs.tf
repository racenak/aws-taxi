output "batch_service_role_arn" {
  value = aws_iam_role.batch_service_role.arn
}

output "batch_execution_role_arn" {
  value = aws_iam_role.batch_execution_role.arn
}

output "batch_job_role_arn" {
  value = aws_iam_role.batch_job_role.arn
}

output "batch_compute_environment_arn" {
  value = aws_batch_compute_environment.fargate_env.arn
}

output "batch_job_queue_arn" {
  value = aws_batch_job_queue.batch_queue.arn
}

output "batch_job_definition_arn" {
  value = aws_batch_job_definition.job_def.arn
}