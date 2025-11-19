import requests
import sys

# Replace this with your actual API key from https://openweathermap.org/api
API_KEY = "e6ef1a61edaa0473b70f69ba4a9ba263"

# Default city (you can pass another one as an argument)
city = sys.argv[1] if len(sys.argv) > 1 else "vadodara"

# You can switch between different endpoints:
#   - Current weather: api.openweathermap.org/data/2.5/weather
#   - Forecast:        api.openweathermap.org/data/2.5/forecast
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Construct the full URL
params = {
    "q": city,
    "appid": API_KEY,
    "units": "metric"  # use "imperial" for °F
}

print(f"🔍 Fetching weather data for: {city}...\n")

try:
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()  # raise exception for HTTP errors
    data = response.json()

    # Basic weather details
    weather = data["weather"][0]["description"].capitalize()
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    print(f"🌤  Weather: {weather}")
    print(f"🌡  Temperature: {temp}°C (Feels like {feels_like}°C)")
    print(f"💧  Humidity: {humidity}%")
    print(f"💨  Wind speed: {wind_speed} m/s")
    print(f"🏙  Location: {data['name']}, {data['sys']['country']}")

except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP error occurred: {http_err}")
    print("Response:", response.text)
except requests.exceptions.RequestException as req_err:
    print(f"⚠️  Request error: {req_err}")
except KeyError:
    print("⚠️  Unexpected response format. Full response:")
    print(data)
