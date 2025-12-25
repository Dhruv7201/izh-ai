import aiohttp
import json
from app.config.settings import settings

FOURSQUARE_API_KEY = settings.FOURSQUARE_API_KEY


async def fetch_foursquare(session, lat, lng):
    url = "https://places-api.foursquare.com/places/search"
    
    headers = {
        "X-Places-Api-Version": "2025-06-17",
        "accept": "application/json",
        "Authorization": f"Bearer {FOURSQUARE_API_KEY}"
    }
    
    params = {
        "ll": f"{lat},{lng}",
        "limit": 50
    }
    
    async with session.get(url, headers=headers, params=params) as resp:
        data = await resp.json()
        
        results = data.get("results", [])
        pois = []
        
        for r in results:
            location = r.get("location", {})
            pois.append({
                "source": "foursquare",
                "id": r.get("fsq_id"),
                "name": r.get("name"),
                "lat": float(location.get("latitude", 0)),
                "lng": float(location.get("longitude", 0)),
                "rating": float(r.get("rating", 0)) if r.get("rating") else 0,
                "address": location.get("formatted_address"),
                "categories": [c.get("name") for c in r.get("categories", [])],
            })
        
        return pois