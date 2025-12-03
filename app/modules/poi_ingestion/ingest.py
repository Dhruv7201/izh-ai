
import asyncio
import aiohttp
from pymongo import MongoClient

from google_places import fetch_google_places
from foursquare import fetch_foursquare
from tripadvisor import fetch_tripadvisor
from normalizer import normalize
from app.config.settings import settings


async def ingest_destination(name, lat, lng):
    async with aiohttp.ClientSession() as session:

        print(f"\n🔍 Fetching Google Places for {name}...")
        google_pois = await fetch_google_places(name, lat, lng)

        print(f"🔍 Fetching Foursquare for {name}...")
        foursquare_pois = await fetch_foursquare(lat, lng)

        print(f"🔍 Fetching TripAdvisor for {name}...")
        tripadvisor_pois = await fetch_tripadvisor(lat, lng)
        all_raw = google_pois + foursquare_pois + tripadvisor_pois
        print(f"📦 Total raw POIs fetched: {len(all_raw)}")

        normalized = [normalize(p) for p in all_raw]

        client = MongoClient(settings.mongodb_url)
        print(f"Connected to MongoDB: {settings.mongodb_url}")
        db = client[settings.MONGODB_DB]
        col = db["pois"]

        if normalized:
            col.insert_many(normalized)

        print(f"✅ Inserted {len(normalized)} normalized POIs for {name} into MongoDB.")


async def main():
    destinations = [
        ("golden temple", 31.6200, 74.8765)
    ]

    coros = [ingest_destination(name, lat, lng) for name, lat, lng in destinations]
    await asyncio.gather(*coros)
