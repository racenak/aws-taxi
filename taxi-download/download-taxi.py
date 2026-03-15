import os
import requests
import logging
import boto3
from botocore.exceptions import ClientError

# Cấu hình Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
# Lấy từ Environment Variables trên Lambda Console
S3_BUCKET = os.environ.get("S3_BUCKET")
BASE_URL  = "https://d37ci6vzurychx.cloudfront.net"

# Khởi tạo S3 Client
s3_client = boto3.client('s3')

def stream_download_and_upload(year: int, month: str):
    file_name = f"yellow_tripdata_{year}-{month}.parquet"
    file_url  = f"{BASE_URL}/trip-data/{file_name}"
    s3_key    = f"{year}/{file_name}"

    try:
        logger.info(f"Starting stream download & upload for {file_name}...")

        # Sử dụng requests để stream dữ liệu
        with requests.get(file_url, stream=True, timeout=300) as response:
            response.raise_for_status()
            
            # Đẩy stream trực tiếp vào S3 bằng upload_fileobj
            # response.raw là file-like object
            s3_client.upload_fileobj(
                response.raw, 
                S3_BUCKET, 
                s3_key,
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )

        logger.info(f"Successfully uploaded to s3://{S3_BUCKET}/{s3_key}")
        return True

    except Exception as e:
        logger.error(f"Error processing {file_name}: {str(e)}")
        return False

def lambda_handler(event, context):
    """
    Hàm entry point cho Lambda. 
    Bạn có thể truyền year và month qua 'event' nếu muốn chạy lẻ,
    hoặc để mặc định chạy theo dải năm/tháng.
    """
    # Lấy thông số từ event (nếu có), nếu không dùng mặc định
    start_year = event.get('start_year', 2025)
    end_year   = event.get('end_year', 2025)
    
    success_count = 0
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            month_str = f"{month:02d}"
            if stream_download_and_upload(year, month_str):
                success_count += 1

    return {
        'statusCode': 200,
        'body': f"Finished processing. Uploaded {success_count} files."
    }