import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key


TABLE_NAME = os.environ.get("TABLE_NAME", "cville-weather")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
PLOT_KEY = os.environ.get("PLOT_KEY", "dp3/cville-weather/latest.svg")

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")


def to_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def c_to_f(celsius):
    if celsius is None:
        return None
    return round((float(celsius) * 9 / 5) + 32, 2)


def fetch_weather():
    params = {
        "latitude": 38.0293,
        "longitude": -78.4767,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": "America/New_York",
    }

    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def save_weather_record(weather_data):
    table = dynamodb.Table(TABLE_NAME)
    current = weather_data["current"]

    timestamp = current.get("time") or datetime.now(timezone.utc).isoformat()

    temp_c = current.get("temperature_2m")
    temp_f = c_to_f(temp_c)

    item = {
        "signal_type": "current_weather",
        "timestamp": timestamp,
        "temperature_c": to_decimal(temp_c),
        "temperature_f": to_decimal(temp_f),
        "humidity": to_decimal(current.get("relative_humidity_2m")),
        "precipitation": to_decimal(current.get("precipitation")),
        "wind_speed": to_decimal(current.get("wind_speed_10m")),
        "weather_code": to_decimal(current.get("weather_code")),
        "location": "Charlottesville, VA",
        "source": "Open-Meteo",
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=item)
    return item


def get_recent_records(limit=24):
    table = dynamodb.Table(TABLE_NAME)

    response = table.query(
        KeyConditionExpression=Key("signal_type").eq("current_weather"),
        ScanIndexForward=False,
        Limit=limit,
    )

    records = response.get("Items", [])
    records.reverse()
    return records


def make_svg_plot(records):
    width = 900
    height = 420
    margin_left = 70
    margin_right = 30
    margin_top = 50
    margin_bottom = 70

    temps = [float(r["temperature_f"]) for r in records if "temperature_f" in r]

    if not temps:
        temps = [0]

    min_temp = min(temps)
    max_temp = max(temps)

    if min_temp == max_temp:
        min_temp -= 1
        max_temp += 1

    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    points = []
    labels = []

    for i, record in enumerate(records):
        temp = float(record["temperature_f"])
        x = margin_left + (i / max(len(records) - 1, 1)) * plot_width
        y = margin_top + ((max_temp - temp) / (max_temp - min_temp)) * plot_height
        points.append(f"{x:.1f},{y:.1f}")

        ts = record["timestamp"]
        time_label = ts[-5:] if len(ts) >= 5 else ts
        labels.append((x, time_label))

    point_string = " ".join(points)

    latest = records[-1] if records else {}
    latest_temp = latest.get("temperature_f", "N/A")
    latest_wind = latest.get("wind_speed", "N/A")
    latest_precip = latest.get("precipitation", "N/A")
    latest_time = latest.get("timestamp", "N/A")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold">
    Charlottesville Weather Pulse
  </text>
  <text x="{width/2}" y="52" text-anchor="middle" font-family="Arial" font-size="13">
    Latest: {latest_temp}°F | Wind: {latest_wind} km/h | Precip: {latest_precip} mm | {latest_time}
  </text>

  <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height-margin_bottom}" stroke="black"/>
  <line x1="{margin_left}" y1="{height-margin_bottom}" x2="{width-margin_right}" y2="{height-margin_bottom}" stroke="black"/>

  <text x="20" y="{margin_top + 10}" font-family="Arial" font-size="12">{max_temp:.1f}°F</text>
  <text x="20" y="{height - margin_bottom}" font-family="Arial" font-size="12">{min_temp:.1f}°F</text>

  <polyline points="{point_string}" fill="none" stroke="black" stroke-width="3"/>
'''

    for point in points:
        x, y = point.split(",")
        svg += f'  <circle cx="{x}" cy="{y}" r="4" fill="black"/>\n'

    if labels:
        first_x, first_label = labels[0]
        last_x, last_label = labels[-1]
        svg += f'  <text x="{first_x}" y="{height - 35}" text-anchor="middle" font-family="Arial" font-size="12">{first_label}</text>\n'
        svg += f'  <text x="{last_x}" y="{height - 35}" text-anchor="middle" font-family="Arial" font-size="12">{last_label}</text>\n'

    svg += f'''
  <text x="{width/2}" y="{height - 12}" text-anchor="middle" font-family="Arial" font-size="12">
    Temperature trend from recent ingestions
  </text>
</svg>'''

    return svg


def upload_plot(svg):
    if not BUCKET_NAME:
        raise ValueError("BUCKET_NAME environment variable is required")

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=PLOT_KEY,
        Body=svg.encode("utf-8"),
        ContentType="image/svg+xml",
        CacheControl="no-cache",
    )

    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{PLOT_KEY}"


def lambda_handler(event, context):
    weather_data = fetch_weather()
    saved_item = save_weather_record(weather_data)

    records = get_recent_records()
    svg = make_svg_plot(records)
    plot_url = upload_plot(svg)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Weather data ingested successfully",
                "saved_item": {
                    "signal_type": saved_item["signal_type"],
                    "timestamp": saved_item["timestamp"],
                    "temperature_f": float(saved_item["temperature_f"]),
                    "humidity": float(saved_item["humidity"]),
                    "precipitation": float(saved_item["precipitation"]),
                    "wind_speed": float(saved_item["wind_speed"]),
                    "location": saved_item["location"],
                },
                "plot_url": plot_url,
            }
        ),
    }


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(json.dumps(result, indent=2))
