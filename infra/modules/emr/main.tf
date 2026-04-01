# # 1. Trust Policy: Cho phép dịch vụ EMR Serverless giả định (Assume) Role này
# data "aws_iam_policy_document" "emr_assume_role" {
#   statement {
#     actions = ["sts:AssumeRole"]
#     principals {
#       type        = "Service"
#       identifiers = ["emr-serverless.amazonaws.com"]
#     }
#   }
# }

# # 2. IAM Role cho Job Execution
# resource "aws_iam_role" "emr_serverless_role" {
#   name               = "${var.app_name}-execution-role"
#   assume_role_policy = data.aws_iam_policy_document.emr_assume_role.json
# }

# # 3. Policy Quyền hạn: Cho phép đọc/ghi S3 và Log vào CloudWatch
# resource "aws_iam_policy" "emr_serverless_policy" {
#   name        = "${var.app_name}-policy"
#   description = "Quyen han cho EMR Serverless truy cap S3 va Logs"

#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject"]
#         Effect   = "Allow"
#         Resource = ["${var.s3_bucket_arn}", "${var.s3_bucket_arn}/*"]
#       },
#       {
#         Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
#         Effect   = "Allow"
#         Resource = ["arn:aws:logs:*:*:*"]
#       }
#     ]
#   })
# }

# # 4. Gắn Policy vào Role
# resource "aws_iam_role_policy_attachment" "emr_attach" {
#   role       = aws_iam_role.emr_serverless_role.name
#   policy_arn = aws_iam_policy.emr_serverless_policy.arn
# }

# # 5. Khởi tạo EMR Serverless Application
# resource "aws_emrserverless_application" "this" {
#   name          = var.app_name
#   release_label = var.release_label
#   type          = "spark"

#   initial_capacity {
#     initial_capacity_type = "Driver"
#     initial_capacity_config {
#       worker_count = 1
#       worker_configuration {
#         cpu    = "1 vCPU"
#         memory = "4 GB"
#       }
#     }
#   }
# }