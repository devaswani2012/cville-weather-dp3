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
        "about": "Charlottesville Weather Pulse tracks current weather conditions in Charlottesville, VA over time using Open-Meteo, DynamoDB, Lambda, S3, and Chalice.",
        "resources": ["current", "history", "stats", "plot"]
    }


@app.route("/current")
def current():
    records = get_recent_records(limit=1)

    if not records:
        return {"response": "No weather records found yet."}

    r = records[0]
    return {
        "response": f"Current Charlottesville weather: {r.get('temperature_f')}°F, humidity {r.get('humidity')}%, wind speed {r.get('wind_speed')} km/h, precipitation {r.get('precipitation')} mm. Last updated: {r.get('timestamp')}."
    }


@app.route("/history")
def history():
    query_params = app.current_request.query_params or {}
    limit = int(query_params.get("limit", 5))

    if limit < 1:
        limit = 1
    if limit > 10:
        limit = 10

    records = get_recent_records(limit=limit)

    summary = []
    for r in records:
        summary.append(
            f"{r.get('timestamp')}: {r.get('temperature_f')}°F, humidity {r.get('humidity')}%, wind {r.get('wind_speed')} km/h"
        )

    return {
        "response": summary
    }


@app.route("/stats")
def stats():
    records = get_recent_records(limit=24)

    if not records:
        return {"response": "No records available for stats yet."}

    temps = [r["temperature_f"] for r in records if "temperature_f" in r]
    humidity = [r["humidity"] for r in records if "humidity" in r]
    wind = [r["wind_speed"] for r in records if "wind_speed" in r]

    response_text = (
        f"Based on the latest {len(records)} records: "
        f"temperature avg {round(sum(temps) / len(temps), 2)}°F "
        f"(min {min(temps)}°F, max {max(temps)}°F); "
        f"humidity avg {round(sum(humidity) / len(humidity), 2)}%; "
        f"wind speed avg {round(sum(wind) / len(wind), 2)} km/h."
    )

    return {
        "response": response_text
    }


@app.route("/plot")
def plot():
    plot_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{PLOT_KEY}"
    return {
        "response": plot_url
    }
