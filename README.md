# Charlottesville Weather Pulse

## Project Overview

Charlottesville Weather Pulse is a serverless cloud application that monitors current weather conditions in Charlottesville, Virginia. The project uses a scheduled AWS Lambda function to collect current weather data from the Open-Meteo API, stores timestamped observations in DynamoDB, generates a live SVG temperature trend plot, uploads the plot to S3, and exposes the results through a Chalice-powered REST API.

## Live API

Base URL:

```text
https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/
```

## API Resources

### 1. Root Resource

```bash
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/
```

Returns project metadata and the available API resources.

### 2. Current Weather

```bash
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/current
```

Returns the most recent weather observation stored in DynamoDB.

### 3. Weather History

```bash
curl "https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/history?limit=5"
```

Returns recent timestamped weather observations. The `limit` parameter controls how many records are returned.

### 4. Weather Statistics

```bash
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/stats
```

Returns summary statistics for recent records, including temperature, humidity, and wind speed.

### 5. Public Plot

```bash
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/plot
```

Returns the public S3 URL for the latest generated weather trend plot.

Direct public plot URL:

```text
https://cville-weather-plots-devaswani.s3.amazonaws.com/dp3/cville-weather/latest.svg
```

## Architecture

The application has two main cloud components:

### 1. Scheduled Ingestion Lambda

The ingestion Lambda runs on an Amazon EventBridge schedule. Each time it runs, it:

1. Calls the Open-Meteo API for current Charlottesville weather.
2. Extracts temperature, humidity, precipitation, wind speed, and weather code.
3. Stores the timestamped record in DynamoDB.
4. Queries recent records from DynamoDB.
5. Generates an SVG temperature trend plot.
6. Uploads the plot to an S3 bucket.

### 2. Chalice REST API

The Chalice API provides public endpoints for accessing the stored weather data. It reads from DynamoDB and returns JSON responses for current weather, weather history, summary statistics, and the public S3 plot URL.

## AWS Services Used

- AWS Lambda
- Amazon EventBridge
- Amazon DynamoDB
- Amazon S3
- Amazon API Gateway
- AWS Chalice
- IAM

## Data Source

This project uses the Open-Meteo forecast API to retrieve current weather data for Charlottesville, Virginia.

Location used:

- Latitude: `38.0293`
- Longitude: `-78.4767`

Current weather fields ingested:

- Temperature
- Relative humidity
- Precipitation
- Weather code
- Wind speed

## DynamoDB Schema

Table name:

```text
cville-weather
```

Primary key:

```text
Partition key: signal_type
Sort key: timestamp
```

Example record:

```json
{
  "signal_type": "current_weather",
  "timestamp": "2026-05-05T14:30",
  "temperature_f": 82.04,
  "temperature_c": 27.8,
  "humidity": 23,
  "precipitation": 0,
  "wind_speed": 25.1,
  "weather_code": 1,
  "location": "Charlottesville, VA",
  "source": "Open-Meteo"
}
```

## S3 Plot

The ingestion Lambda generates a public SVG plot showing the recent temperature trend.

Public S3 object:

```text
s3://cville-weather-plots-devaswani/dp3/cville-weather/latest.svg
```

Public URL:

```text
https://cville-weather-plots-devaswani.s3.amazonaws.com/dp3/cville-weather/latest.svg
```

## EventBridge Schedule

The ingestion Lambda is triggered by the following EventBridge rule:

```text
cville-weather-ingest-schedule
```

Schedule expression:

```text
rate(1 hour)
```

This allows the project to continuously collect new weather records over time.

## Local Development

### Run the ingestion script locally

From the project root:

```bash
export TABLE_NAME=cville-weather
export BUCKET_NAME=cville-weather-plots-devaswani
export PLOT_KEY=dp3/cville-weather/latest.svg

python ingestion/lambda_function.py
```

### Run the API locally

```bash
cd api/cville-weather-api
chalice local
```

Then test local endpoints:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/current
curl "http://127.0.0.1:8000/history?limit=5"
curl http://127.0.0.1:8000/plot
curl http://127.0.0.1:8000/stats
```

## Deployment

### Deploy the API

From the Chalice app directory:

```bash
cd api/cville-weather-api
chalice deploy
```

The deployed API is available at:

```text
https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/
```

### Test the deployed API

```bash
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/current
curl "https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/history?limit=5"
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/plot
curl https://0g7w2898b3.execute-api.us-east-1.amazonaws.com/api/stats
```

## Project Structure

```text
cville-weather-pulse/
├── README.md
├── ingestion/
│   └── lambda_function.py
└── api/
    └── cville-weather-api/
        ├── app.py
        ├── requirements.txt
        └── .chalice/
            ├── config.json
            └── policy-dev.json
```

## Summary

This project satisfies the DP3 requirements by implementing a serverless data pipeline with scheduled ingestion, persistent cloud storage, a public REST API with multiple resources, and a publicly accessible S3 visualization.
