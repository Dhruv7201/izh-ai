import aiohttp
from app.config.settings import settings

TA_BASE = "https://tripadvisor16.p.rapidapi.com/api/v1"

TA_HEADERS = {
    "X-RapidAPI-Key": settings.TRIPADVISOR_API_KEY,
    "X-RapidAPI-Host": "tripadvisor16.p.rapidapi.com"
}

async def fetch_tripadvisor(session, lat, lng):
    url = f"{TA_BASE}/location/nearby_search"
    params = {"latLong": f"{lat},{lng}"}

    async with session.get(url, headers=TA_HEADERS, params=params) as resp:
        data = await resp.json()
        results = data.get("data", [])
        pois = []

        for p in results:
            pois.append({
                "source": "tripadvisor",
                "id": p.get("location_id"),
                "name": p.get("name"),
                "lat": float(p.get("latitude")),
                "lng": float(p.get("longitude")),
                "rating": float(p.get("rating", 0)),
                "address": p.get("address"),
                "categories": [c.get("name") for c in p.get("category", [])],
            })

    return pois
