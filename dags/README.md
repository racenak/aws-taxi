# NYC Yellow Taxi ETL Pipeline - Airflow DAGs

This directory contains Airflow DAGs for orchestrating the complete ETL pipeline for NYC Yellow Taxi data processing.

## Overview

### Pipeline Stages

1. **Ingest**: Download taxi data from public source to S3 (Bronze layer)
2. **Transformation**:
   - **Clean**: Validate and clean Bronze data → Silver layer (Iceberg)
   - **Load**: Enrich Silver data with taxi zone info → Gold layer (Iceberg)
   - **Aggregate**: Create aggregated analytics views → Agg layer (Iceberg)

### DAGs

#### 1. `taxi_etl_dag.py` (Production DAG)

Scheduled weekly ETL pipeline with full end-to-end processing.

- **Schedule**: Weekly (configurable)
- **Tasks**:
  - Download taxi data
  - Clean & validate
  - Load & enrich
  - Aggregate
  - Data quality checks

#### 2. `taxi_etl_backfill.py` (Backfill DAG)

Manual DAG for backfilling specific months or re-running stages.

- **Schedule**: Manual trigger only
- **Parameters**: `year`, `month`, `stage`
- **Use cases**:
  - Backfill historical data
  - Re-run failed stages
  - Process specific months

## Setup

### 1. Set Airflow Variables

Set these variables in Airflow UI or via CLI:

```bash
# S3 Configuration
airflow variables set "taxi_s3_bucket" "my-taxi-bucket"
airflow variables set "taxi_s3_raw_prefix" "raw/taxi"
airflow variables set "taxi_s3_bronze_prefix" "bronze/taxi"

# Iceberg Configuration
airflow variables set "iceberg_catalog" "prod_catalog"

# Lookup Data
airflow variables set "taxi_zone_csv_path" "s3://my-bucket/lookup/taxi-zones.csv"

# Job Scripts (paths on Airflow worker)
airflow variables set "taxi_download_script" "/opt/airflow/jobs/taxi-download/download_with_partition.py"
airflow variables set "clean_script" "/opt/airflow/jobs/job/clean.py"
airflow variables set "load_script" "/opt/airflow/jobs/job/load.py"
airflow variables set "agg_script" "/opt/airflow/jobs/job/agg_table.py"
```

Or use Python:

```bash
cd dags/
python config.py  # Prints all commands needed
```

### 2. Enable Connection to Spark/YARN

Ensure your Airflow worker can access:

- Spark/YARN cluster
- S3 bucket (with proper IAM credentials)
- Iceberg catalog

### 3. Copy Job Scripts

Place job scripts in accessible locations on Airflow workers:

```bash
/opt/airflow/jobs/
├── taxi-download/
│   └── download_with_partition.py
└── job/
    ├── clean.py
    ├── load.py
    └── agg_table.py
```

## Usage

### Run Production DAG

```bash
# Trigger manually
airflow dags trigger taxi_etl_pipeline

# Check execution
airflow dags list
airflow task list taxi_etl_pipeline
```

### Run Backfill DAG

```bash
# Backfill full year 2024
airflow dags trigger \
    --exec-date 2024-01-01 \
    taxi_etl_backfill \
    --conf '{"year": 2024, "stage": "all"}'

# Backfill specific month only
airflow dags trigger \
    --exec-date 2024-03-01 \
    taxi_etl_backfill \
    --conf '{"year": 2024, "month": 3, "stage": "all"}'

# Re-run only aggregation stage
airflow dags trigger \
    --exec-date 2024-03-01 \
    taxi_etl_backfill \
    --conf '{"year": 2024, "month": 3, "stage": "aggregate"}'
```

## DAG Visualization

### `taxi_etl_dag.py` Flow

```
start
  ↓
[Ingest]
  ├── download_taxi_data
  ↓
[Transformation]
  ├── clean_data
  ├── load_data
  ├── aggregate_data
  ↓
check_gold_table
  ↓
end
```

### `taxi_etl_backfill.py` Flow

```
extract_config
  ↓
[Ingest]
  ├── download_taxi_year
  ↓
[Transformation]
  ├── clean_data → load_data → aggregate_data
  ↓
validate_tables
  ↓
end
```

## Monitoring & Logs

### Check DAG Runs

```bash
# List recent runs
airflow dags list-runs -d taxi_etl_pipeline

# Get task logs
airflow tasks logs taxi_etl_pipeline download_taxi_data 2024-01-01
```

### Troubleshooting

**Issue**: Task fails with Spark connection error

- **Solution**: Check Spark/YARN cluster accessibility from Airflow worker
- **Logs**: `airflow tasks logs taxi_etl_pipeline clean_data YYYY-MM-DD`

**Issue**: S3 upload fails

- **Solution**: Verify S3 credentials and bucket access
- **Check**: `aws s3 ls s3://your-bucket/`

**Issue**: Iceberg table not found

- **Solution**: Verify catalog configuration and table exists
- **Check**: `spark-sql -e "SHOW TABLES IN catalog.schema;"`

## Configuration Details

### Spark Submit Parameters

```yaml
Master: YARN (cluster)
Deploy Mode: cluster
Num Executors: 4 (clean/load), 2 (aggregate)
Executor Memory: 2G
Driver Memory: 1G
```

Adjust based on your cluster size and data volume.

### Schedule

Default: Weekly on Monday

- **Modify in `taxi_etl_dag.py`**: Change `schedule_interval` parameter
- **Cron examples**:
  - Daily: `"@daily"`
  - Weekly Monday: `"0 0 * * 1"`
  - Monthly: `"0 0 1 * *"`

## Data Flow

```
Public NYC Taxi Data
  ↓
[Download]
  ↓
S3 Bronze (raw-data)
  ↓
[Clean & Validate]
  ↓
Iceberg Silver (cleaned)
  ↓
[Enrich with Taxi Zones]
  ↓
Iceberg Gold (enriched)
  ↓
[Aggregate]
  ↓
Iceberg Agg (analytics views)
```

## Environment Variables

Set in Airflow `env` or worker environment:

```bash
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## References

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [Apache Iceberg](https://iceberg.apache.org/)
- [NYC Taxi Data](https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
