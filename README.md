# aws-taxi

## Overview

**aws-taxi** is a complete data engineering solution for analyzing NYC Yellow Taxi data using AWS services. This project demonstrates a modern data pipeline architecture that automates the ingestion, processing, storage, and analysis of large-scale transportation datasets.

### Key Features

- **Automated Data Pipeline**: Download and process NYC Yellow Taxi data using Apache Airflow orchestration
- **Scalable Processing**: Leverage Apache Spark for distributed data transformation and aggregation
- **Cloud Infrastructure**: Fully managed AWS infrastructure using Terraform (S3, EMR, Athena, Batch, Glue, etc.)
- **Data Storage**: Partitioned data storage in S3 with Athena for fast SQL queries
- **Interactive Analytics**: Power BI dashboards for geographic and temporal analysis of taxi patterns
- **Containerized Deployment**: Docker containers for reliable and reproducible data downloads

### Project Goals

- Process millions of NYC Yellow Taxi trip records efficiently
- Enable exploratory analysis of taxi demand patterns by borough and time
- Demonstrate best practices for cloud-based data engineering
- Provide reproducible infrastructure-as-code setup for the entire pipeline

## Architecture
![Architecture](.\media\Architecture.svg)

## Folder Structure

This project uses a modular architecture to manage AWS infrastructure and data pipeline operations for NYC Yellow Taxi analysis. Here's what each folder contains:

### `/infra` - Infrastructure as Code
Contains Terraform configurations for AWS resources:
- **`global/`** - Global resources and base configurations
- **`env/`** - Environment-specific configurations (dev, staging, prod)
- **`modules/`** - Reusable Terraform modules:
  - `airflow/` - Apache Airflow orchestration setup
  - `athena/` - AWS Athena query configuration
  - `batch/` - AWS Batch job definitions
  - `ecr/` - Elastic Container Registry setup
  - `emr/` - EMR cluster configuration
  - `event-bridge/` - EventBridge rules and targets
  - `glue/` - AWS Glue jobs and data catalog
  - `s3/` - S3 bucket configurations
  - `vpc/` - VPC and networking setup

### `/script` - Data Processing Scripts
Contains orchestration and job scripts:
- **`airflow/`** - Apache Airflow DAGs (Directed Acyclic Graphs)
  - `dags/` - Workflow definitions for scheduling data pipelines
- **`sparkjobs/`** - Apache Spark jobs for data processing:
  - `load.py` - Load raw taxi data into data warehouse
  - `clean.py` - Data cleaning and transformation
  - `agg_table.py` - Aggregation and summary tables

### `/athena` - SQL Queries
Pre-written SQL queries for AWS Athena analysis:
- `create_database_table.sql` - Database and table schema definitions
- `agg_taxi_borough_monthly.sql` - Monthly borough-level aggregations

### `/taxi-download` - Data Download Container
Docker container for downloading NYC Yellow Taxi data:
- `Dockerfile` - Container image definition
- `download_with_partition.py` - Script to fetch and partition taxi data
- `requirements.txt` - Python dependencies

### `/powerbi` - Business Intelligence
Power BI dashboards and reports:
- `NYC Yellow Taxi — Geographic Analysis.pbix` - Interactive geographic analysis dashboard

### `/media` - Documentation Assets
Images and media files:
- `Dashboard.JPG` - Dashboard screenshots and documentation images
- `Architecture.svg` - System Architecture

## Getting Started

### Prerequisite
- AWS CLI - 2.x.x
- Terraform with AWS profile can request resources
- Windows 64 bit ODBC driver 2.x
- PowerBI
- Docker (optional)

### Request Resources on AWS
- Create a folder infra/env/dev. Create a file named `main.tf` with content
```
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "your-current-terraform-version"
    }
  }
}

provider "aws" {
  region = "your-aws-region"
  profile = "your-name-aws-profile"
}
```
- Run `terraform init` to install terraform for manage resources on AWS. After complete run `terrform apply` to see what resources will install on AWS and type `yes` for installation and waiting to complete

### Setup lakehouse
- Go to Athena service and run SQL `create_database_table.sql` for create silver and gold layer in lakehouse. Notice: Replace `bucket-name` with your bucket name in S3

### Ingest
- Make sure `taxi-download` image build and push into `ECR` through Github Action
- AWS Batch will run container and download taxi data as parquet format and load into folder `raw` in S3 bucket

### Transform
- Use EMR with serverless application for run Spark jobs via AWS CLI:
Clean taxi data:
```
aws emr-serverless start-job-run \
    --application-id <APPLICATION_ID> \
    --execution-role-arn <EXECUTION_ROLE_ARN> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "s3://your-script-bucket-name/sparkjobs/clean.py",
            "entryPointArguments": [
                "--bronze-path", "s3://your-data-bucket-name/raw/raw-yellow-taxi/",
                "--silver_full_ref", "catalog.silver.yellow_taxi",
                "--incremental-col", "tpep_pickup_datetime"
            ]
        }
    }'
```
Load into `gold table` with `One Big Table schema`, notice you need to download `taxi_zone_lookup.csv` :
```
aws emr-serverless start-job-run \
    --application-id <APPLICATION_ID> \
    --execution-role-arn <EXECUTION_ROLE_ARN> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "s3://your-script-bucket-name/sparkjobs/load.py",
            "entryPointArguments": [
                "--silver_full_ref", "catalog.silver.yellow_taxi",
                "--gold_full_ref", "catalog.gold.yellow_taxi",
                "--s3_taxi_zone_csv", "s3://your-data-bucket-name/raw/taxi-zone-lookup/taxi_zone_lookup.csv"
            ]
        }
    }'
```

### Load
Agg table ready for dashboard visualize:
```
aws emr-serverless start-job-run \
    --application-id <APPLICATION_ID> \
    --execution-role-arn <EXECUTION_ROLE_ARN> \
    --job-driver '{
        "sparkSubmit": {
            "entryPoint": "s3://your-script-bucket-name/sparkjobs/agg_table.py",
            "entryPointArguments": [
                "--gold_full_ref", "catalog.gold.yellow_taxi",
                "--agg_full_ref", "catalog.agg.yellow_taxi"
            ]
        }
    }'
```

### Visualization
- User PowerBI connect to Athena with `Data Connectvity Mode` is `Import`
![Dashboard](.\media\Dashboard.JPG)

### Auto Workflow
- Use Airflow for automation these task