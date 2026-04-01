import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

from pyspark.functions import col, year, month

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
dyf = glueContext.create_dynamic_frame.from_catalog(database='test', table_name='raw_data_898653659022_ap_southeast_1_an')
df = dyf.toDF()

standard_trip = df.filter((col("RatecodeID") == 1) & 
                          (col("improvement_surcharge") == 1.0) & 
                          (col("fare_amount") >= 3.0)
                          )

jfk = df.filter((col("RatecodeID") == 2) & 
                (col("Airport_fee") != -1.75) & 
                (col("mta_tax") == 0.5) & 
                (col("fare_amount") == 70.0) 
                )

newark = df.filter((col("RatecodeID") == 3) & 
                   (col("fare_amount") >= 0.0) & 
                   (col("improvement_surcharge") >= 0.0)
                    )

nassau_westchester = df.filter((col("RatecodeID") == 4) & 
                              (col("mta_tax") == 0.5) & 
                              (col("improvement_surcharge") == 1.0)
                              )

outside = df.filter((col("RatecodeID") == 5) & 
                    (col("mta_tax") >= 0.5) & 
                    (col("improvement_surcharge") == 1.0)
                    )

group_ride = df.filter(col("RatecodeID") == 6)

merged_trips = (
    standard_trip
    .unionByName(jfk)
    .unionByName(newark)
    .unionByName(nassau_westchester)
    .unionByName(outside)
    .unionByName(group_ride)
    .orderBy("tpep_pickup_datetime")
)

merged_trips = merged_trips.filter(col("payment_type").isin([1, 2]))

merged_trips.write.mode("overwrite").parquet("s3://processed-data-898653659022-ap-southeast-1-an/")