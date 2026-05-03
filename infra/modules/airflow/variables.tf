variable "script_bucket_arn" {
  description = "ARN of the S3 bucket where Airflow scripts are stored"
  type        = string
}

variable "security_group" {
  type = list(string)
}

variable "private_subnets" {
  type = list(string)
}

variable "batch_job_queue_arn" {
  type = string
}

variable "batch_job_definition_arn" {
  type = string
}