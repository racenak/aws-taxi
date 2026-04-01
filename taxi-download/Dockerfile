# Sử dụng base image Python của AWS Lambda (chọn kiến trúc arm64 để tiết kiệm chi phí)
FROM public.ecr.aws/docker/library/python:3.11.2-alpine

WORKDIR /app

# Copy file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện (requests, boto3, ...)
RUN pip install --no-cache-dir -r requirements.txt

# Copy file code của bạn vào container
COPY download-taxi.py .
