import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from chalice import Chalice


app = Chalice(app_name="cville-weather-api")
app.api.cors = True

TABLE_NAME = os.environ.get("TABLE_NAME", "cville-weather")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "cville-weather-plots-devaswani")
PLOT_KEY = os.environ.get("PLOT_KEY", "dp3/cville-weather/latest.svg")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def clean_decimal(value):
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, list):
        return [clean_decimal(v) for v in value]

    if isinstance(value, dict):
        return {k: clean_decimal(v) for k, v in value.items()}

    return value


def get_recent_records(limit=10):
    response = table.query(
        KeyConditionExpression=Key("signal_type").eq("current_weather"),
        ScanIndexForward=False,
        Limit=limit,
    )

    records = response.get("Items", [])
    return [clean_decimal(record) for record in records]


@app.route("/")
def index():
    return {
        "project": "Charlottesville Weather Pulse",
        "description": "A serverless weather monitor that ingests current Charlottesville weather, stores records in DynamoDB, and publishes a live trend plot to S3.",
        "data_source": "Open-Meteo forecast API",
        "resources": {
            "current": "/current",
            "history": "/history?limit=10",
            "plot": "/plot",
            "stats": "/stats"
        }
    }


@app.route("/current")
def current():
    records = get_recent_records(limit=1)

    if not records:
        return {
            "message": "No weather records found yet. Run the ingestion Lambda first."
        }

    return {
        "latest_record": records[0]
    }


@app.route("/history")
def history():
    query_params = app.current_request.query_params or {}
    limit = int(query_params.get("limit", 10))

    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50

    records = get_recent_records(limit=limit)

    return {
        "count": len(records),
        "records": records
    }


@app.route("/plot")
def plot():
    plot_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{PLOT_KEY}"

    return {
        "plot_url": plot_url,
        "message": "Public S3 URL for the latest generated weather trend plot."
    }


@app.route("/stats")
def stats():
    records = get_recent_records(limit=24)

    if not records:
        return {
            "message": "No records available for stats yet."
        }

    temps = [r["temperature_f"] for r in records if "temperature_f" in r]
    humidity = [r["humidity"] for r in records if "humidity" in r]
    wind = [r["wind_speed"] for r in records if "wind_speed" in r]

    return {
        "record_count": len(records),
        "temperature_f": {
            "min": min(temps),
            "max": max(temps),
            "avg": round(sum(temps) / len(temps), 2)
        },
        "humidity": {
            "min": min(humidity),
            "max": max(humidity),
            "avg": round(sum(humidity) / len(humidity), 2)
        },
        "wind_speed": {
            "min": min(wind),
            "max": max(wind),
            "avg": round(sum(wind) / len(wind), 2)
        }
    }
