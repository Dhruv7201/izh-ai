import sys
sys.path.append("/home/dhruv/workspace/izh")
import aiohttp
from app.config.settings import settings
import asyncio

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
        print(details)
        exit()
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
            "user_ratings_total": r.get("user_ratings_total", 0),
            "reviews": r.get("reviews", [])
        }


if __name__ == "__main__":
    import sys
    import asyncio
    import aiohttp

    sys.path.append("/home/dhruv/workspace/izh")

    from app.modules.poi_ingestion.sentiment_analysis import (
        analyze_reviews_sentiment_without_storage
    )
    from app.modules.poi_ingestion.tripadvisor import search_locations
    from app.modules.poi_ingestion.google_places import fetch_google_places
    from app.config.settings import settings


    async def get_google_place_id(session, destination, lat, lng):
        """
        Fetch first Google place_id for a destination
        """
        BASE = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": destination,
            "location": f"{lat},{lng}",
            "radius": 8000,
            "key": settings.GOOGLE_PLACES_API_KEY
        }

        async with session.get(BASE, params=params) as resp:
            data = await resp.json()
            results = data.get("results", [])

            if not results:
                return None

            return results[0]["place_id"]


    async def get_tripadvisor_location_id(session, name, lat, lng):
        """
        Fetch first TripAdvisor location_id
        """
        results = await search_locations(session, name, lat, lng)
        if not results:
            return None

        return str(results[0].get("locationId") or results[0].get("location_id"))


    async def main():
        async with aiohttp.ClientSession() as session:
            destination = "Gateway of India"
            lat, lng = 18.921984, 72.834654

            # 1️⃣ Get IDs
            google_place_id = await get_google_place_id(
                session, destination, lat, lng
            )
            tripadvisor_location_id = await get_tripadvisor_location_id(
                session, destination, lat, lng
            )

            print("Google place_id:", google_place_id)
            print("TripAdvisor location_id:", tripadvisor_location_id)

            # 2️⃣ Run sentiment analysis (NO STORAGE)
            result = await analyze_reviews_sentiment_without_storage(
                session=session,
                google_place_id=google_place_id,
                tripadvisor_location_id=tripadvisor_location_id,
                language="en"
            )

            # 3️⃣ Print output
            print("\n===== STATISTICS =====")
            print(result["statistics"])

            print("\n===== SAMPLE REVIEWS =====")
            for r in result["reviews"][:3]:
                print({
                    "source": r.get("source"),
                    "rating": r.get("rating"),
                    "sentiment": r.get("sentiment_score"),
                    "text": r.get("text")[:120]
                })

    asyncio.run(main())