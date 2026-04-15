CREATE TABLE nyc_taxi.cleaned_yellow_taxi (
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
    cbd_congestion_fee double
)
PARTITIONED BY (month(tpep_pickup_datetime))
LOCATION 's3://iceberg-warehouse-898653659022-ap-southeast-1-an/cleaned/cleaned-yellow-taxi/'
TBLPROPERTIES (
  'table_type'='ICEBERG'
);

ALTER TABLE nyc_taxi.cleaned_yellow_taxi 
UNSET TBLPROPERTIES ('write.object-storage.path');

ALTER TABLE nyc_taxi.cleaned_yellow_taxi 
SET TBLPROPERTIES ('write.data.path'='s3://iceberg-warehouse-898653659022-ap-southeast-1-an/cleaned/cleaned-yellow-taxi/data');

