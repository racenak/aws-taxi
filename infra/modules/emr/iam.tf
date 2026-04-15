resource "aws_iam_role" "emr_service_role" {
  name = "${var.app_name}-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "elasticmapreduce.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "emr_service_s3_policy" {
  name        = "${var.app_name}-service-s3-policy"
  description = "Cho phep EMR Service Role truy cap bucket workspace"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:GetEncryptionConfiguration",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Effect   = "Allow"
        Resource = [
          "${var.script_bucket_arn}",
          "${var.script_bucket_arn}/*"
        ]
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "service_managed_attach" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceEditorsRole"
}

resource "aws_iam_role_policy_attachment" "studio_service_custom_s3_attach" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = aws_iam_policy.emr_service_s3_policy.arn
}



# 2. Runtime Execution Role (Dùng cho cả Studio User và EMR Serverless Job)
resource "aws_iam_role" "execution_role" {
  name = "${var.app_name}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = ["elasticmapreduce.amazonaws.com", "emr-serverless.amazonaws.com"] }
    }]
  })
}

# Policy cho Glue, S3, Logs 
resource "aws_iam_policy" "combined_policy" {
  name   = "${var.app_name}-combined-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:DeleteObject"]
        Effect   = "Allow"
        Resource = ["${var.iceberg_warehouse_bucket_arn}", "${var.iceberg_warehouse_bucket_arn}/*"]
      },
      {
        Action   = ["glue:GetDatabase", 
                    "glue:CreateTable", 
                    "glue:GetTable", 
                    "glue:GetTables",
                    "glue:UpdateTable", 
                    "glue:DeleteTable",
                    "glue:GetUserDefinedFunctions", 
                    "glue:GetPartitions"
                    ]
        Effect   = "Allow"
        Resource = ["*"] # Có thể giới hạn hẹp hơn theo ARN database
      },
      {
        Action   = ["logs:CreateLogGroup", 
                    "logs:CreateLogStream", 
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams"
                  ]
        Effect   = "Allow"
        Resource = ["arn:aws:logs:*:*:*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "execution_attach" {
  role       = aws_iam_role.execution_role.name
  policy_arn = aws_iam_policy.combined_policy.arn
}

# 1. Tạo IAM User cho Admin
resource "aws_iam_user" "emr_admin" {
  name = "${var.app_name}-admin-user"
  path = "/"

  tags = {
    Role = "EMR-Admin"
  }
}

# 2. Chuyển đổi Policy JSON mẫu sang Terraform Resource
resource "aws_iam_policy" "emr_admin_management_policy" {
  name        = "${var.app_name}-admin-management-policy"
  description = "Policy cho phep Admin quan ly EMR Serverless va Studio"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowServerlessActions"
        Effect = "Allow"
        Action = [
          "emr-serverless:CreateApplication",
          "emr-serverless:UpdateApplication",
          "emr-serverless:DeleteApplication",
          "emr-serverless:ListApplications",
          "emr-serverless:GetApplication",
          "emr-serverless:StartApplication",
          "emr-serverless:StopApplication",
          "emr-serverless:StartJobRun",
          "emr-serverless:CancelJobRun",
          "emr-serverless:ListJobRuns",
          "emr-serverless:GetJobRun",
          "emr-serverless:GetDashboardForJobRun",
          "emr-serverless:AccessInteractiveEndpoints"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowStudioandWorkspaceActions"
        Effect = "Allow"
        Action = [
          "elasticmapreduce:CreateEditor",
          "elasticmapreduce:DescribeEditor",
          "elasticmapreduce:ListEditors",
          "elasticmapreduce:UpdateStudio",
          "elasticmapreduce:StartEditor",
          "elasticmapreduce:StopEditor",
          "elasticmapreduce:DeleteEditor",
          "elasticmapreduce:OpenEditorInConsole",
          "elasticmapreduce:AttachEditor",
          "elasticmapreduce:DetachEditor",
          "elasticmapreduce:CreateStudio",
          "elasticmapreduce:DescribeStudio",
          "elasticmapreduce:DeleteStudio",
          "elasticmapreduce:ListStudios",
          "elasticmapreduce:CreateStudioPresignedUrl"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowPassingRoles"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.execution_role.arn,             
          aws_iam_role.emr_service_role.arn    
        ]
      },
      {
        Sid    = "AllowS3ListAndGetPermissions"
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::*"
      },
      {
        Sid    = "DescribeNetworkAndIAM"
        Effect = "Allow"
        Action = [
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "iam:ListRoles"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowEC2ENICreation"
        Effect = "Allow"
        Action = "ec2:CreateNetworkInterface"
        Resource = [
          "arn:aws:ec2:*:*:subnet/*",
          "arn:aws:ec2:*:*:security-group/*",
          "arn:aws:ec2:*:*:network-interface/*"
        ]
      },
      {
        Sid    = "AllowSLRCreation"
        Effect = "Allow"
        Action = "iam:CreateServiceLinkedRole"
        Resource = "arn:aws:iam::*:role/aws-service-role/ops.emr-serverless.amazonaws.com/AWSServiceRoleForAmazonEMRServerless"
      }
    ]
  })
}

# 3. Gán Policy vào User Admin
resource "aws_iam_user_policy_attachment" "admin_attach" {
  user       = aws_iam_user.emr_admin.name
  policy_arn = aws_iam_policy.emr_admin_management_policy.arn
}

# 4. (Tùy chọn) Tạo Login Profile để đăng nhập Console
resource "aws_iam_user_login_profile" "admin_login" {
  user            = aws_iam_user.emr_admin.name
  password_length = 16
  # Lưu ý: Password sẽ hiện trong state file hoặc output. 
  # Nên dùng 'terraform output' để lấy mật khẩu lần đầu.
}

output "admin_password" {
  value     = aws_iam_user_login_profile.admin_login.password
  sensitive = false
}
