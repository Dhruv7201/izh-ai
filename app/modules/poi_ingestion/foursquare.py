import sys
sys.path.append("/home/dhruv/workspace/izh/")
import requests
import json
from app.config.settings import settings

FOURSQUARE_API_KEY = settings.FOURSQUARE_API_KEY


def fetch_foursquare(lat, lng, radius=1000, limit=50):
    url = "https://places-api.foursquare.com/places/search"

    headers = {
        "X-Places-Api-Version": "2025-06-17",
        "accept": "application/json",
        "Authorization": f"Bearer {FOURSQUARE_API_KEY}"
    }

    params = {
        "ll": f"{lat},{lng}",
        "radius": radius,        # meters
        "limit": limit,
        "categories": "16000"    # Foursquare Category: "Arts & Entertainment"
                                # includes attractions, museums, landmarks, etc.
    }
    print("=== REQUEST DETAILS ===")
    print("URL:", url)
    print("Headers:", headers)
    print("Params:", params)
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"FSQ API Error: {response.status_code} - {response.text}")

    data = response.json()
    return data.get("results", [])
