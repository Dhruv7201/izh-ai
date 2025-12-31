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


async def ingest_destination(city_name: str, ingestion_date=None, grid_size: float = DEFAULT_GRID_SIZE):
    """
    Ingest POIs for a city using grid-based approach and store in PostgreSQL with distance-based clustering.
    
    Args:
        city_name: City name (e.g., "Amritsar")
        ingestion_date: Date of ingestion (defaults to today). Used for monthly tracking.
        grid_size: Grid step size in degrees (default ~1km)
    """
    if ingestion_date is None:
        ingestion_date = date.today()
    
    logger.info(f"Starting ingestion for city: {city_name} on {ingestion_date}")
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Fetch city boundaries
        print(f"\n📍 Fetching city boundaries for {city_name}...")
        city_data = await fetch_city_boundaries(session, city_name)
        
        if not city_data:
            logger.error(f"Failed to fetch boundaries for {city_name}")
            return
        
        bounds = city_data["bounds"]
        city_location = city_data["location"]
        city_center_lat = city_location["lat"]
        city_center_lng = city_location["lng"]
        
        print(f"✅ City boundaries: NE({bounds['northeast']['lat']}, {bounds['northeast']['lng']}), "
              f"SW({bounds['southwest']['lat']}, {bounds['southwest']['lng']})")
        
        # Step 2: Generate grid points
        print(f"\n🔲 Generating grid points (grid_size={grid_size})...")
        grid_points = generate_grid_points(bounds, grid_size)
        print(f"✅ Generated {len(grid_points)} grid points")
        
        if not grid_points:
            logger.warning(f"No grid points generated for {city_name}")
            return
        
        # Step 3: Fetch POIs for each grid point
        print(f"\n🔍 Fetching POIs from {len(grid_points)} grid points...")
        all_raw_pois = []
        seen_poi_ids = set()  # Deduplicate by source_id
        
        # Process grid points in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(grid_points), batch_size):
            batch = grid_points[i:i + batch_size]
            tasks = [fetch_pois_search_nearby(session, lat, lng) for lat, lng in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in batch: {result}")
                    continue
                
                for poi in result:
                    # Deduplicate by source_id
                    poi_id = poi.get("id")
                    if poi_id and poi_id not in seen_poi_ids:
                        seen_poi_ids.add(poi_id)
                        all_raw_pois.append(poi)
            
            # Small delay to respect rate limits
            if i + batch_size < len(grid_points):
                await asyncio.sleep(0.1)
        
        print(f"📦 Total unique POIs fetched: {len(all_raw_pois)}")
        
        if not all_raw_pois:
            print(f"⚠️ No POIs found for {city_name}")
            return
        
        # Step 4: Normalize POIs
        normalized = [normalize(p) for p in all_raw_pois]
        print(f"✅ Normalized {len(normalized)} POIs")
        
        # Step 5: Prepare POIs for clustering
        pois_for_clustering = [
            {
                "lat": p["poi"]["lat"],
                "lng": p["poi"]["lng"],
                "name": p["poi"]["name"],
                "poi_uuid": p["poi"]["poi_uuid"]
            }
            for p in normalized
        ]
        
        # Step 6: Cluster POIs based on distance
        print(f"🔗 Clustering {len(pois_for_clustering)} POIs based on geographic distance...")
        clusters = cluster_pois(pois_for_clustering)
        print(f"✅ Created {len(clusters)} distance-based clusters")
        
        # Step 7: Create cluster_id mapping using poi_uuid
        poi_to_cluster = {}
        for cluster in clusters:
            cluster_id = cluster["cluster_id"]
            for poi in cluster["pois"]:
                poi_uuid = poi["poi_uuid"]
                poi_to_cluster[poi_uuid] = cluster_id
        
        # Step 8: Get or create city record
        city_id = await get_or_create_city(city_name, city_center_lat, city_center_lng, city_data["formatted_address"])
        
        # Step 9: Store in database with transaction
        inserted_count = 0
        updated_count = 0
        
        async with query_executor.transaction() as conn:
            for norm_data in normalized:
                poi_data = norm_data["poi"]
                details_data = norm_data["details"]
                
                # Get cluster_id for this POI using UUID
                cluster_id = poi_to_cluster.get(poi_data["poi_uuid"], None)
                
                # Check if POI already exists
                existing_poi_query = """
                    SELECT id FROM pois 
                    WHERE source = $1 AND source_id = $2
                """
                existing_poi = await conn.fetchrow(
                    existing_poi_query,
                    poi_data["source"],
                    poi_data["source_id"]
                )
                
                is_new = existing_poi is None
                
                # Insert or update into pois table
                poi_insert_query = """
                    INSERT INTO pois (
                        destination_name, destination_lat, destination_lng,
                        poi_uuid, source, source_id, name, lat, lng,
                        rating, address, cluster_id, ingestion_date, city_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (source, source_id) DO UPDATE SET
                        destination_name = EXCLUDED.destination_name,
                        destination_lat = EXCLUDED.destination_lat,
                        destination_lng = EXCLUDED.destination_lng,
                        name = EXCLUDED.name,
                        lat = EXCLUDED.lat,
                        lng = EXCLUDED.lng,
                        rating = EXCLUDED.rating,
                        address = EXCLUDED.address,
                        cluster_id = EXCLUDED.cluster_id,
                        ingestion_date = EXCLUDED.ingestion_date,
                        city_id = EXCLUDED.city_id,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """
                
                try:
                    poi_id = await conn.fetchval(
                        poi_insert_query,
                        city_name,  # destination_name
                        float(city_center_lat),  # destination_lat
                        float(city_center_lng),  # destination_lng
                        poi_data["poi_uuid"],  # poi_uuid
                        poi_data["source"],  # source
                        poi_data["source_id"],  # source_id
                        poi_data["name"],  # name
                        poi_data["lat"],  # lat
                        poi_data["lng"],  # lng
                        poi_data["rating"],  # rating
                        poi_data["address"],  # address
                        cluster_id,  # cluster_id
                        ingestion_date,  # ingestion_date
                        city_id  # city_id
                    )
                    
                    if poi_id:
                        if is_new:
                            inserted_count += 1
                        else:
                            updated_count += 1
                        
                        # Insert or update into poi_details table
                        details_insert_query = """
                            INSERT INTO poi_details (
                                poi_id, categories, opening_hours,
                                duration_minutes, best_time, photos, user_ratings_total
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                            ON CONFLICT (poi_id) DO UPDATE SET
                                categories = EXCLUDED.categories,
                                opening_hours = EXCLUDED.opening_hours,
                                duration_minutes = EXCLUDED.duration_minutes,
                                best_time = EXCLUDED.best_time,
                                photos = EXCLUDED.photos,
                                user_ratings_total = EXCLUDED.user_ratings_total,
                                updated_at = CURRENT_TIMESTAMP
                        """
                        
                        await conn.execute(
                            details_insert_query,
                            poi_id,  # poi_id
                            json.dumps(details_data["categories"]),  # categories
                            json.dumps(details_data["opening_hours"]),  # opening_hours
                            details_data["duration_minutes"],  # duration_minutes
                            json.dumps(details_data["best_time"]),  # best_time
                            json.dumps(details_data["photos"]),  # photos
                            details_data["user_ratings_total"]  # user_ratings_total
                        )
                except Exception as e:
                    logger.error(f"⚠️ Error inserting/updating POI {poi_data.get('name', 'unknown')}: {e}")
                    continue
        
        logger.info(
            f"✅ Completed ingestion for {city_name}: "
            f"Inserted {inserted_count} new POIs, "
            f"Updated {updated_count} existing POIs, "
            f"Total clusters: {len(clusters)}, "
            f"City ID: {city_id}"
        )


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
