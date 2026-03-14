# aws-taxi

# OICD Identity Provider setup
IAM → Identity Providers → Add provider
Provider URL: https://token.actions.githubusercontent.com
Audience: sts.amazonaws.com

# IAM Role for GitHub Actions
IAM → Roles → Create role
Web identity
Provider: token.actions.githubusercontent.com
Audience: sts.amazonaws.com