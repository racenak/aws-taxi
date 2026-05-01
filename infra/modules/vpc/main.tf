resource "aws_vpc" "main_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

# Tạo Subnet công cộng để Batch Job có thể truy cập Internet
resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "ap-southeast-1c"
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main_vpc.id
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_security_group" "batch_sg" {
  name        = "batch-job-sg"
  description = "Cho phep Batch Job truy cap internet de tai file"
  vpc_id      = aws_vpc.main_vpc.id

  # Cho phép mọi traffic đi ra ngoài (để tải file từ Internet và đẩy lên S3)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Tạo 2 Private Subnets ở 2 AZ khác nhau 
resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "ap-southeast-1a"

  tags = { Name = "airflow-private-1" }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "ap-southeast-1b"

  tags = { Name = "airflow-private-2" }
}

# Tạo Route Table cho Private Zone ---
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main_vpc.id

  tags = { Name = "airflow-private-rt" }
}

# Liên kết Route Table với cả 2 Private Subnets
resource "aws_route_table_association" "private_assoc_1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_assoc_2" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private_rt.id
}

# S3 Gateway Endpoint (Quan trọng cho Airflow & Batch) ---
resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id            = aws_vpc.main_vpc.id
  service_name      = "com.amazonaws.ap-southeast-1.s3"
  vpc_endpoint_type = "Gateway"

  # Gắn vào cả Route Table của Public (cho Batch) và Private (cho Airflow)
  route_table_ids = [ 
    aws_route_table.private_rt.id
  ]

  tags = { Name = "s3-endpoint" }
}

# Security Group cho Airflow (Web UI chi cho phep IP cua ban truy cap) ---
resource "aws_security_group" "airflow_sg" {
  name        = "airflow-public-web-sg"
  description = "Security group cho Airflow voi Web UI truy cap cong cong"
  vpc_id      = aws_vpc.main_vpc.id

  # Chi cho phep IP cua ban truy cap vao UI
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["${var.your_ip}/32"] # Thay bang IP cua ban (check tai whatismyip.com)
    description = "Only allow my IP to access Airflow UI"
  }

  # Cho phep cac thanh phan noi bo lien lac (Self-reference)
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # Cho phep Airflow ra ngoai internet (de goi API Batch, tai plugin,...)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "airflow-sg-public"
  }
}