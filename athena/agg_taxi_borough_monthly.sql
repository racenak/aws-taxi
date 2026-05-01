CREATE TABLE agg_yellow_taxi_borough_monthly(
  pickup_year     INT,
  pickup_month    INT,
  pickup_borough  STRING,
  dropoff_borough STRING,
  total_trips     BIGINT,
  total_revenue   DOUBLE,
  total_trip_distance  DOUBLE,
  total_passengers BIGINT
)
LOCATION 's3://bucket-name/gold.db/agg_yellow_taxi_borough_monthly/'
TBLPROPERTIES (
'table_type'='ICEBERG',
'format'='parquet', 
'write_compression'='snappy', 
'write.data.path' = 's3://bucket-name/gold.db/agg_yellow_taxi_borough_monthly/data/',
);

MERGE INTO agg_yellow_taxi_borough_monthly AS t
USING (
  SELECT
    pickup_year,
    pickup_month,
    pickup_borough,
    dropoff_borough,
    COUNT(trip_id)     AS total_trips,
    SUM(total_amount)  AS total_revenue,
    SUM(trip_distance) AS total_trip_distance,
    SUM(passenger_count) AS total_passengers
  FROM obt_yellow_taxi
  FOR VERSION AS OF 3585048462116944344
  GROUP BY 1,2,3,4
) AS s
ON  t.pickup_year    = s.pickup_year
AND t.pickup_month   = s.pickup_month
AND t.pickup_borough = s.pickup_borough
AND t.dropoff_borough= s.dropoff_borough
WHEN MATCHED THEN UPDATE SET
  total_trips   = s.total_trips,
  total_revenue = s.total_revenue,
  avg_revenue   = s.avg_revenue
WHEN NOT MATCHED THEN INSERT VALUES (
  s.pickup_year, s.pickup_month, s.pickup_borough,
  s.dropoff_borough, s.total_trips, s.total_revenue, s.avg_revenue
);