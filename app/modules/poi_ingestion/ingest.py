import sys
sys.path.append("/home/dhruv/workspace/izh")
import asyncio
import aiohttp
import json
import logging
from datetime import date
from typing import List, Dict, Tuple, Optional
from app.helpers.db_executor import query_executor
from app.config.database import db_config
from app.config.settings import settings

from normalizer import normalize
from poi_cluster_engine import cluster_pois

logger = logging.getLogger(__name__)

# Grid size in degrees (approximately 1km = 0.009 degrees)
DEFAULT_GRID_SIZE = 0.009  # ~1km grid
SEARCH_RADIUS_METERS = 1000  # 1km radius for searchNearby


async def fetch_city_boundaries(session: aiohttp.ClientSession, city_name: str) -> Optional[Dict]:
    """
    Fetch city boundaries using Google Geocoding API.
    
    Returns:
        Dict with 'bounds' (northeast, southwest) and 'location' (lat, lng) or None
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": city_name,
        "key": settings.GOOGLE_PLACES_API_KEY
    }
    
    try:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                logger.error(f"Geocoding failed for {city_name}: {data.get('status')}")
                return None
            
            result = data["results"][0]
            geometry = result.get("geometry", {})
            bounds = geometry.get("bounds")
            
            if not bounds:
                # Fallback to viewport if bounds not available
                bounds = geometry.get("viewport", {})
            
            if not bounds:
                logger.error(f"No bounds found for {city_name}")
                return None
            
            location = geometry.get("location", {})
            
            return {
                "bounds": {
                    "northeast": {
                        "lat": bounds["northeast"]["lat"],
                        "lng": bounds["northeast"]["lng"]
                    },
                    "southwest": {
                        "lat": bounds["southwest"]["lat"],
                        "lng": bounds["southwest"]["lng"]
                    }
                },
                "location": {
                    "lat": location.get("lat"),
                    "lng": location.get("lng")
                },
                "formatted_address": result.get("formatted_address", city_name)
            }
    except Exception as e:
        logger.error(f"Error fetching city boundaries for {city_name}: {e}")
        return None


def point_inside_city_boundary(lat: float, lng: float, bounds: Dict) -> bool:
    """
    Check if a point is inside city boundary using bounds.
    
    Args:
        lat: Latitude of the point
        lng: Longitude of the point
        bounds: Dict with 'northeast' and 'southwest' keys
        
    Returns:
        True if point is inside boundary, False otherwise
    """
    ne = bounds["northeast"]
    sw = bounds["southwest"]
    
    return (sw["lat"] <= lat <= ne["lat"] and 
            sw["lng"] <= lng <= ne["lng"])


def generate_grid_points(bounds: Dict, grid_size: float = DEFAULT_GRID_SIZE) -> List[Tuple[float, float]]:
    """
    Generate grid points within city boundaries.
    
    Args:
        bounds: Dict with 'northeast' and 'southwest' keys
        grid_size: Grid step size in degrees (default ~1km)
        
    Returns:
        List of (lat, lng) tuples
    """
    ne = bounds["northeast"]
    sw = bounds["southwest"]
    
    grid_points = []
    
    # Iterate from south to north
    lat = sw["lat"]
    while lat <= ne["lat"]:
        # Iterate from west to east
        lng = sw["lng"]
        while lng <= ne["lng"]:
            if point_inside_city_boundary(lat, lng, bounds):
                grid_points.append((lat, lng))
            lng += grid_size
        lat += grid_size

    return grid_points


async def fetch_pois_search_nearby(session: aiohttp.ClientSession, lat: float, lng: float) -> List[Dict]:
    """
    Fetch POIs using Google Places API searchNearby endpoint.
    
    Args:
        session: aiohttp session
        lat: Latitude
        lng: Longitude
        
    Returns:
        List of POI dictionaries
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.rating,places.formattedAddress,places.regularOpeningHours,places.types,places.photos,places.userRatingCount"
    }
    
    payload = {
        "includedTypes": [
            "tourist_attraction",
            "restaurant",
            "museum",
            "park",
            "shopping_mall",
            "amusement_park",
            "zoo",
            "aquarium",
            "art_gallery",
            "church",
            "hindu_temple",
            "mosque",
            "synagogue",
            "stadium",
            "casino",
            "night_club",
            "bar",
            "cafe"
        ],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng
                },
                "radius": SEARCH_RADIUS_METERS
            }
        }
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.warning(f"searchNearby API error for ({lat}, {lng}): {resp.status} - {error_text}")
                return []
            
            data = await resp.json()
            places = data.get("places", [])
            
            # Transform to our format
            pois = []
            for place in places:
                location = place.get("location", {})
                display_name = place.get("displayName", {})
                opening_hours = place.get("regularOpeningHours", {})
                
                # Skip if no location data
                if not location.get("latitude") or not location.get("longitude"):
                    continue
                
                pois.append({
                    "source": "google",
                    "id": place.get("id"),
                    "name": display_name.get("text", "") if isinstance(display_name, dict) else str(display_name) if display_name else "",
                    "lat": location.get("latitude"),
                    "lng": location.get("longitude"),
                    "rating": place.get("rating"),
                    "address": place.get("formattedAddress", ""),
                    "opening_hours": opening_hours.get("weekdayDescriptions", []) if isinstance(opening_hours, dict) else [],
                    "types": place.get("types", []),
                    "photos": place.get("photos", []),
                    "user_ratings_total": place.get("userRatingCount", 0),
                    "reviews": []  # searchNearby doesn't return reviews
                })
            
            return pois
    except Exception as e:
        logger.error(f"Error fetching POIs for ({lat}, {lng}): {e}")
        return []




async def get_or_create_city(city_name: str, lat: float, lng: float, formatted_address: str) -> int:
    """
    Get or create a city record in the database.
    
    Returns:
        city_id (int)
    """
    query = "INSERT INTO cities (name, lat, lng, formatted_address, created_at) VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP) RETURNING id"
    return await query_executor.fetch_val(query, city_name, lat, lng, formatted_address)

async def main():
    """
    Main function to ingest cities.
    This function can be called monthly to refresh POI data for all cities.
    """
    # List of cities to ingest (city names only)
    cities = [
        # "Amritsar",
        "Vadodara",
        # Add more cities as needed
    ]

    # Get current ingestion date (for monthly tracking)
    ingestion_date = date.today()
    logger.info(f"Starting monthly ingestion process on {ingestion_date}")
    logger.info(f"Processing {len(cities)} city/cities")

    # Process all cities concurrently
    coros = [ingest_destination(city_name, ingestion_date) for city_name in cities]
    await asyncio.gather(*coros)
    
    logger.info("✅ Monthly ingestion process completed")


if __name__ == "__main__":
    asyncio.run(main())
