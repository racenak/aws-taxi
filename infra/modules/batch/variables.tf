variable "vpc_id" {
  type        = string
}

variable "subnet_ids" {
  type        = list(string)
}

variable "security_group_ids" {
  type        = list(string)
}

variable "repository_url" {
  type    = string
}
variable "target_s3_bucket_name" {
  type    = string
}