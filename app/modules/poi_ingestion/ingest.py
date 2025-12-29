import sys
sys.path.append("/home/dhruv/workspace/izh")
import asyncio
import aiohttp
import json
import logging
from datetime import date
from app.helpers.db_executor import query_executor
from app.config.database import db_config

from google_places import fetch_google_places
from foursquare import fetch_foursquare
from tripadvisor import fetch_tripadvisor
from normalizer import normalize
from poi_cluster_engine import cluster_pois

logger = logging.getLogger(__name__)


async def ingest_destination(name, lat, lng, ingestion_date=None):
    """
    Ingest POIs for a destination and store in PostgreSQL with distance-based clustering.
    
    Args:
        name: Destination name
        lat: Destination latitude
        lng: Destination longitude
        ingestion_date: Date of ingestion (defaults to today). Used for monthly tracking.
    """
    if ingestion_date is None:
        ingestion_date = date.today()
    
    # Ensure database is connected
    # if not db_config._initialized:
    #     await db_config.connect()
    
    logger.info(f"Starting ingestion for destination: {name} ({lat}, {lng}) on {ingestion_date}")
    
    async with aiohttp.ClientSession() as session:
        print(f"\n🔍 Fetching Google Places for {name}...")
        google_pois = await fetch_google_places(session, name, lat, lng)

        print(f"🔍 Fetching Foursquare for {name}...")
        # foursquare_pois = await fetch_foursquare(session, lat, lng)
        foursquare_pois = []

        print(f"🔍 Fetching TripAdvisor for {name}...")
        tripadvisor_pois = await fetch_tripadvisor(session, lat, lng, location_name=name)
        
        all_raw = google_pois + foursquare_pois + tripadvisor_pois
        print(f"📦 Total raw POIs fetched: {len(all_raw)}")

        if not all_raw:
            print(f"⚠️ No POIs found for {name}")
            return

        # Normalize POIs
        normalized = [normalize(p) for p in all_raw]
        print(f"✅ Normalized {len(normalized)} POIs")

        # Prepare POIs for clustering (need lat/lng)
        pois_for_clustering = [
            {
                "lat": p["poi"]["lat"],
                "lng": p["poi"]["lng"],
                "name": p["poi"]["name"],
                "poi_uuid": p["poi"]["poi_uuid"]  # Use UUID for mapping
            }
            for p in normalized
        ]

        # Cluster POIs based on distance (no num_days parameter)
        print(f"🔗 Clustering {len(pois_for_clustering)} POIs based on geographic distance...")
        clusters = cluster_pois(pois_for_clustering)
        print(f"✅ Created {len(clusters)} distance-based clusters")

        # Create cluster_id mapping using poi_uuid
        # cluster_id is now a string like "cluster_1", "cluster_2", etc.
        poi_to_cluster = {}
        for cluster in clusters:
            cluster_id = cluster["cluster_id"]  # e.g., "cluster_1"
            for poi in cluster["pois"]:
                poi_uuid = poi["poi_uuid"]
                poi_to_cluster[poi_uuid] = cluster_id
        print("poi_to_cluster")
        print(poi_to_cluster)

        # Store in database with transaction
        inserted_count = 0
        updated_count = 0
        
        # async with query_executor.transaction() as conn:
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
            # On conflict, update existing POI with new data and ingestion_date
            poi_insert_query = """
                INSERT INTO pois (
                    destination_name, destination_lat, destination_lng,
                    poi_uuid, source, source_id, name, lat, lng,
                    rating, address, cluster_id, ingestion_date
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
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
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """
            
            try:
                poi_id = await conn.fetchval(
                    poi_insert_query,
                    name,  # destination_name
                    float(lat),  # destination_lat
                    float(lng),  # destination_lng
                    poi_data["poi_uuid"],  # poi_uuid
                    poi_data["source"],  # source
                    poi_data["source_id"],  # source_id
                    poi_data["name"],  # name
                    poi_data["lat"],  # lat
                    poi_data["lng"],  # lng
                    poi_data["rating"],  # rating
                    poi_data["address"],  # address
                    cluster_id,  # cluster_id
                    ingestion_date  # ingestion_date
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
            f"✅ Completed ingestion for {name}: "
            f"Inserted {inserted_count} new POIs, "
            f"Updated {updated_count} existing POIs, "
            f"Total clusters: {len(clusters)}"
        )


async def main():
    """
    Main function to ingest destinations.
    This function can be called monthly to refresh POI data for all destinations.
    """
    # Ensure database is connected
    # if not db_config._initialized:
    #     await db_config.connect()
    
    # List of destinations to ingest
    # Format: (name, lat, lng)
    destinations = [
        # ("golden temple", 31.6200, 74.8765),  # name, lat, lng
        # Add more destinations as needed
        ("vadodara", 22.3072, 73.1812),
    ]

    # Get current ingestion date (for monthly tracking)
    ingestion_date = date.today()
    logger.info(f"Starting monthly ingestion process on {ingestion_date}")
    logger.info(f"Processing {len(destinations)} destination(s)")

    # Process all destinations concurrently
    coros = [ingest_destination(name, lat, lng, ingestion_date) for name, lat, lng in destinations]
    await asyncio.gather(*coros)
    
    logger.info("✅ Monthly ingestion process completed")
    
    # Note: Don't disconnect here if using connection pooling
    # The connection pool will be managed by the application lifecycle


if __name__ == "__main__":
    asyncio.run(main())
