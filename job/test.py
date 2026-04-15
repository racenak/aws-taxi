from pyspark.sql import SparkSession

# 1. Khởi tạo SparkSession với hỗ trợ Hive (để kết nối Glue Catalog)
spark = SparkSession.builder \
    .appName("GlueCatalogReadExample") \
    .enableHiveSupport() \
    .getOrCreate()


try:
    
    # Cách 1: Sử dụng spark.table (Cách gọn nhất)
    df = spark.read.table("glue_catalog.nyc_taxi.raw_yellow_taxi")
    
    # Cách 2: Sử dụng SQL thuần túy (Nếu bạn quen dùng SQL)
    # df = spark.sql(f"SELECT * FROM {glue_database}.{glue_table}")

    # 3. In schema để kiểm tra cấu trúc cột
    schema = df.schema
    for field in schema:
        print(f"Column: {field.name}, Type: {field.dataType}")

    # 4. In 20 dòng dữ liệu đầu tiên ra log (STDOUT)
    df.show(20, truncate=False)

    # 5. Đếm tổng số dòng
    row_count = df.count()
    print(f"--- Tổng số dòng đọc được: {row_count} ---")
    print("--- Đọc dữ liệu thành công từ Glue Catalog! ---")

except Exception as e:
    print(f"Lỗi khi truy cập Glue Catalog: {e}")

finally:
    spark.stop()