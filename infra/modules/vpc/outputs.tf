output "vpc_id" {
  value = aws_vpc.main_vpc.id
}

output "public_subnet_id" {
  value = aws_subnet.public_subnet.id
}

output "batch_security_group_id" {
  value = aws_security_group.batch_sg.id
}

output "airflow_security_group_id" {
  value = aws_security_group.airflow_sg.id
}

output "private_subnet_id" {
  value = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
}
