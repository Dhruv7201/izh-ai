import aiohttp
from app.config.settings import settings

BASE = "https://maps.googleapis.com/maps/api/place"

GOOGLE_SEARCH_QUERIES = [
    "top attractions",
    # "tourist places",
    # "landmarks",
    # "things to do",
    # "historical places",
    # "viewpoints",
    # "parks",
    # "museums",
]

async def fetch_google_places(session, destination, lat, lng, radius=8000):
    all_results = []

    for query in GOOGLE_SEARCH_QUERIES:
        params = {
            "query": f"{query} in {destination}",
            "location": f"{lat},{lng}",
            "radius": radius,
            "key": settings.GOOGLE_PLACES_API_KEY
        }
        url = f"{BASE}/textsearch/json"
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            results = data.get("results", [])
            all_results.extend(results)

    # Enrich each with place details
    enriched = []
    for r in all_results:
        details = await fetch_details(session, r["place_id"])
        
        if details:
            enriched.append(details)

    return enriched

async def fetch_details(session, place_id):
    url = f"{BASE}/details/json"
    params = {"place_id": place_id, "key": settings.GOOGLE_PLACES_API_KEY}

    async with session.get(url, params=params) as resp:
        data = await resp.json()
        
        r = data.get("result")
        if not r:
            return None

        return {
            "source": "google",
            "id": r.get("place_id"),
            "name": r.get("name"),
            "lat": r["geometry"]["location"]["lat"],
            "lng": r["geometry"]["location"]["lng"],
            "rating": r.get("rating"),
            "address": r.get("formatted_address"),
            "opening_hours": r.get("opening_hours", {}).get("weekday_text", []),
            "types": r.get("types", []),
            "photos": r.get("photos", []),
            "user_ratings_total": r.get("user_ratings_total", 0)
        }
