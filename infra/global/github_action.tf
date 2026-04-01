# 1. Tạo OIDC Provider cho GitHub Actions
resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub Actions OIDC thumbprint (stable value)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = {
    Environment = "Dev"
    Purpose     = "CI-CD"
  }
}

# 2. Tạo IAM Role (thay thế IAM User)
resource "aws_iam_role" "github_actions_role" {
  name = "github-actions-deployer"
  path = "/system/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:racenak/aws-taxi:*"
          }
        }
      }
    ]
  })

  tags = {
    Environment = "Dev"
    Purpose     = "CI-CD"
  }
}

# 3. Gán Policy vào Role (giữ nguyên permissions)
resource "aws_iam_role_policy" "github_actions_policy" {
  name = "GithubActionsLimitedPolicy"
  role = aws_iam_role.github_actions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      }
    ]
  })
}

# 4. Output Role ARN (không còn secret key nhạy cảm)
output "github_actions_role_arn" {
  value = aws_iam_role.github_actions_role.arn
}