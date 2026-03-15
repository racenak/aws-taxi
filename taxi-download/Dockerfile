# Sử dụng base image Python của AWS Lambda (chọn kiến trúc arm64 để tiết kiệm chi phí)
FROM public.ecr.aws/lambda/python:3.11-arm64

# Copy file requirements.txt vào container
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Cài đặt các thư viện (requests, boto3, ...)
RUN pip install --no-cache-dir -r requirements.txt

# Copy file code của bạn vào container
COPY download-taxi.py ${LAMBDA_TASK_ROOT}

# Thiết lập hàm handler sẽ chạy khi Lambda được gọi
CMD [ "download_taxi.lambda_handler" ]