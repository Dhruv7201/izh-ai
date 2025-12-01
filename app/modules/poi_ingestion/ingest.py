
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
        # google_pois = await fetch_google_places(session, name, lat, lng)

        print(f"🔍 Fetching Foursquare for {name}...")
        foursquare_pois = await fetch_foursquare(session, lat, lng)

        print(f"🔍 Fetching TripAdvisor for {name}...")
        # tripadvisor_pois = await fetch_tripadvisor(session, lat, lng)
        exit()
        all_raw = foursquare_pois # + google_pois + tripadvisor_pois
        print(f"📦 Total raw POIs fetched: {len(all_raw)}")
        exit()

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
        ("golden temple", 31.6200, 74.8765),
        # ("Dubai", 25.2048, 55.2708),
        # ("Bali", -8.3405, 115.0920),
        # ("Phuket", 7.8804, 98.3923),
        # ("London", 51.5072, -0.1276)
    ]

    coros = [ingest_destination(name, lat, lng) for name, lat, lng in destinations]
    await asyncio.gather(*coros)
