import requests
import json
from app.config.settings import settings

FOURSQUARE_API_KEY = settings.FOURSQUARE_API_KEY


def fetch_foursquare(session, lat, lng):
    # URL
    url = "https://places-api.foursquare.com/places/search"

    # Headers (copied from cURL)
    headers = {
        "X-Places-Api-Version": "2025-06-17",
        "accept": "application/json",
        "Authorization": f"Bearer {FOURSQUARE_API_KEY}"
    }

    # Params (add your own if needed)
    params = {
        # Example:
        # "query": "coffee",
        # "ll": "40.7484,-73.9857"
    }

    print("=== REQUEST DETAILS ===")
    print("URL:", url)
    print("HEADERS:", json.dumps(headers, indent=2))
    print("PARAMS:", json.dumps(params, indent=2))

    # API request
    response = requests.get(url, headers=headers, params=params)

    print("\n=== RESPONSE STATUS ===")
    print(response.status_code)

    print("\n=== RESPONSE BODY ===")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

