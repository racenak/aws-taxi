from pyspark.sql import SparkSession
from pyspark.sql.functions import col, year, month

# 1. Khởi tạo SparkSession với hỗ trợ Hive (để kết nối Glue Catalog)
spark = SparkSession.builder \
    .appName("CleanNycTaxi") \
    .enableHiveSupport() \
    .getOrCreate()

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

glue_database = "nyc_taxi"
glue_table = "raw_yellow_taxi_898653659022_ap_southeast_1_an"

df = spark.table(f"{glue_database}.{glue_table}")

standard_trip = df.filter((col("RatecodeID") == 1) & 
                  (col("improvement_surcharge") == 1.0) &
                  (col("mta_tax").isin([0.0, 0.5])) &
                  (col("congestion_surcharge").isin([0.0, 2.5])) &
                  (col("fare_amount") >= 3.0 ) &
                  (col("cbd_congestion_fee").isin([0.0, 0.75]))
) 

jfk = df.filter((col("RatecodeID") == 2) & 
                (col("Airport_fee") >= 0.0) &
                (col("mta_tax").isin([0.0, 0.5])) &
                (col("improvement_surcharge").isin([0.0, 1.0])) &
                (col("congestion_surcharge").isin([0.0, 2.5])) &
                (col("cbd_congestion_fee").isin([0.0, 0.75]))
)

newark = df.filter((col("RatecodeID") == 3) &
                    (col("fare_amount") >= 0.0) &
                   (col("improvement_surcharge") >= 0.0)
)

nassau_westchester = df.filter((col("RatecodeID") == 4) &
                               (col("mta_tax") == 0.5) &
                               (col("improvement_surcharge") == 1.0) &
                               (col("congestion_surcharge").isin([0.0, 2.5])) &
                               (col("cbd_congestion_fee").isin([0.0, 0.75]))
)

outside = df.filter((col("RatecodeID") == 5) &
                    (col("mta_tax").isin([0.0, 0.5])) &
                    (col("improvement_surcharge") == 1.0) &
                    (col("congestion_surcharge").isin([0.0, 2.5])) &
                    (col("cbd_congestion_fee").isin([0.0, 0.75]))
)

merged_trips = (
    standard_trip
    .unionByName(jfk)
    .unionByName(newark)
    .unionByName(nassau_westchester)
    .unionByName(outside)
)

merged_trips = merged_trips.sortWithinPartitions("tpep_pickup_datetime")

final_df = merged_trips.filter(col("payment_type").isin([1, 2])) \
    .withColumn("year", year(col("tpep_pickup_datetime"))) \
    .withColumn("month", month(col("tpep_pickup_datetime")))

final_df = final_df.repartition(1, "year", "month")

final_df.write.mode("overwrite").partitionBy("year", "month").parquet("s3://cleaned-yellow-taxi-898653659022-ap-southeast-1-an/yellow-taxi-data/")