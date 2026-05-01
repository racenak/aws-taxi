CREATE DATABASE IF NOT EXISTS silver
LOCATION 's3://bucket-name/silver.db/';

CREATE TABLE cleaned_yellow_taxi (
    VendorID int,
    tpep_pickup_datetime timestamp,
    tpep_dropoff_datetime timestamp,
    passenger_count bigint,
    trip_distance double,
    RatecodeID bigint,
    store_and_fwd_flag string,
    PULocationID int,
    DOLocationID int,
    payment_type bigint,
    fare_amount double,
    extra double,
    mta_tax double,
    tip_amount double,
    tolls_amount double,
    improvement_surcharge double,
    total_amount double,
    congestion_surcharge double,
    Airport_fee double,
    cbd_congestion_fee double) 
PARTITIONED BY (day(tpep_pickup_datetime))
LOCATION 's3://bucket-name/silver.db/cleaned-yellow-taxi/' 
TBLPROPERTIES (
  'table_type'='ICEBERG',
  'format'='parquet',
  'write_compression'='snappy',
  'write.data.path' = 's3://bucket-name/silver.db/cleaned-yellow-taxi/data/',
  'optimize_rewrite_delete_file_threshold'='10'
)

CREATE DATABASE IF NOT EXISTS gold
LOCATION 's3://bucket-name/gold.db/';

CREATE TABLE obt_yellow_taxi ( 
  trip_id STRING, 
  vendor_id INT, 
  pickup_datetime TIMESTAMP, 
  dropoff_datetime TIMESTAMP, 
  pickup_date DATE, 
  pickup_year INT, 
  pickup_month INT, 
  pickup_day INT, 
  pickup_day_of_week STRING, 
  pickup_hour INT, 
  pickup_location_id INT, 
  pickup_zone STRING, 
  pickup_borough STRING, 
  dropoff_location_id INT, 
  dropoff_zone STRING, 
  dropoff_borough STRING, 
  passenger_count INT, 
  trip_distance DOUBLE, 
  total_amount DOUBLE, 
  payment_type INT, 
  rate_code_id INT, 
  store_and_fwd_flag STRING, 
  data_source STRING, 
  created_at TIMESTAMP) 
PARTITIONED BY (pickup_year, pickup_month) 
LOCATION 's3://bucket-name/gold.db/obt-yellow-taxi/' 
TBLPROPERTIES ( 
  'table_type'='ICEBERG', 
  'format'='parquet', 
  'write_compression'='snappy', 
  'write.data.path' = 's3://bucket-name/gold.db/obt-yellow-taxi/data/',
  'optimize_rewrite_delete_file_threshold'='10' 
)