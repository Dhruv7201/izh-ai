import aiohttp
import logging
from typing import List, Dict, Any, Optional
# from app.config.settings import settings

logger = logging.getLogger(__name__)

TA_BASE = "https://api.content.tripadvisor.com/api/v1"


async def search_locations(session: aiohttp.ClientSession, query: str, lat: Optional[float] = None, lng: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Search for locations on TripAdvisor and return location IDs.
    
    Args:
        session: aiohttp ClientSession
        query: Search query (location name)
        lat: Optional latitude for location-based search
        lng: Optional longitude for location-based search
        
    Returns:
        List of location search results with location_id
    """
    # Try search endpoint first
    url = f"{TA_BASE}/location/search"
    params = {
        "key": "9C06E51AD60E4ED29DFF8FD57D115C60",
        "searchQuery": query,
        "language": "en"
    }
    
    # Add location if provided
    if lat and lng:
        params["latLong"] = f"{lat},{lng}"
    
    try:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                # TripAdvisor API typically returns data in 'data' field
                results = data.get("data", [])
                
                if results:
                    logger.info(f"Found {len(results)} locations for query: {query}")
                    return results
            
            # If search fails and we have coordinates, try nearby_search
            if lat and lng:
                logger.info(f"Search endpoint returned no results, trying nearby_search...")
                return await search_nearby_locations(session, lat, lng)
            
            logger.warning(f"No locations found for query: {query}")
            return []
            
    except Exception as e:
        logger.error(f"Error searching TripAdvisor locations: {e}")
        # Try nearby search as fallback if we have coordinates
        if lat and lng:
            return await search_nearby_locations(session, lat, lng)
        return []


async def search_nearby_locations(session: aiohttp.ClientSession, lat: float, lng: float) -> List[Dict[str, Any]]:
    """
    Search for nearby locations using coordinates.
    
    Args:
        session: aiohttp ClientSession
        lat: Latitude
        lng: Longitude
        
    Returns:
        List of location search results with location_id
    """
    url = f"{TA_BASE}/location/nearby_search"
    params = {
        "key": "9C06E51AD60E4ED29DFF8FD57D115C60",
        "latLong": f"{lat},{lng}",
        "language": "en"
    }
    
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"TripAdvisor nearby_search failed with status {resp.status}")
                return []
            
            data = await resp.json()
            results = data.get("data", [])
            
            if results:
                logger.info(f"Found {len(results)} nearby locations at ({lat}, {lng})")
            
            return results
            
    except Exception as e:
        logger.error(f"Error in nearby search: {e}")
        return []


async def get_location_details(session: aiohttp.ClientSession, location_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific location by ID.
    
    Args:
        session: aiohttp ClientSession
        location_id: TripAdvisor location ID
        
    Returns:
        Location details dictionary or None if error
    """
    url = f"{TA_BASE}/location/{location_id}/details"
    params = {
        "key": "9C06E51AD60E4ED29DFF8FD57D115C60",
        "language": "en"
    }
    
    try:
        print("curl")
        from urllib.parse import urlencode
        print(url+"?"+urlencode(params))
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"TripAdvisor details failed for location {location_id} with status {resp.status}")
                return None
            
            data = await resp.json()
            return data
            
    except Exception as e:
        logger.error(f"Error fetching TripAdvisor location details for {location_id}: {e}")
        return None


async def fetch_tripadvisor(session: aiohttp.ClientSession, lat: float, lng: float, location_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch TripAdvisor POIs by searching for locations and getting their details.
    
    Args:
        session: aiohttp ClientSession
        lat: Latitude for location-based search
        lng: Longitude for location-based search
        location_name: Optional location name to search for (if None, uses coordinates)
        
    Returns:
        List of POI dictionaries in the format expected by the normalizer
    """
    pois = []
    
    # Use location name if provided, otherwise use a generic search
    search_query = location_name if location_name else "attractions"
    
    # Search for locations
    search_results = await search_locations(session, search_query, lat, lng)
    
    if not search_results:
        logger.warning(f"No TripAdvisor locations found for {search_query} at ({lat}, {lng})")
        return pois
    
    # Limit to top 20 results to avoid too many API calls
    max_results = min(20, len(search_results))
    
    # Fetch details for each location
    for result in search_results[:max_results]:
        location_id = result.get("locationId") or result.get("location_id")
        
        if not location_id:
            logger.warning(f"No location_id found in search result: {result}")
            continue
        
        # Get detailed information
        details = await get_location_details(session, str(location_id))
        
        if not details:
            continue
        
        # Extract relevant information from details
        # The API response structure may vary, so we'll handle common fields
        location_data = details.get("data", details)
        
        # Extract coordinates
        location_coords = location_data.get("latitudeLongitude", {})
        poi_lat = location_coords.get("latitude") or result.get("latitude")
        poi_lng = location_coords.get("longitude") or result.get("longitude")
        
        # Extract address
        address_obj = location_data.get("address", {})
        if isinstance(address_obj, dict):
            address_parts = [
                address_obj.get("street1"),
                address_obj.get("city"),
                address_obj.get("country")
            ]
            address = ", ".join(filter(None, address_parts))
        else:
            address = address_obj or result.get("address")
        
        # Extract categories
        categories = []
        category_obj = location_data.get("category", {})
        if isinstance(category_obj, dict):
            categories.append(category_obj.get("name", ""))
        elif isinstance(category_obj, list):
            categories = [c.get("name", "") if isinstance(c, dict) else str(c) for c in category_obj]
        else:
            # Try to get from search result
            cat_list = result.get("category", [])
            if isinstance(cat_list, list):
                categories = [c.get("name", "") if isinstance(c, dict) else str(c) for c in cat_list]
        
        # Extract rating
        rating_obj = location_data.get("rating", {})
        if isinstance(rating_obj, dict):
            rating = float(rating_obj.get("rating", 0))
        else:
            rating = float(rating_obj) if rating_obj else float(result.get("rating", 0))
        
        # Extract review count
        review_count = location_data.get("numberOfReviews", 0) or result.get("num_reviews", 0)
        
        # Extract photos
        photos = []
        photo_obj = location_data.get("photos", [])
        if isinstance(photo_obj, list):
            for photo in photo_obj:
                if isinstance(photo, dict):
                    photo_url = photo.get("images", {}).get("large", {}).get("url") or photo.get("url")
                    if photo_url:
                        photos.append(photo_url)
        
        # Build POI dictionary
        poi = {
            "source": "tripadvisor",
            "id": str(location_id),
            "name": location_data.get("name") or result.get("name", ""),
            "lat": float(poi_lat) if poi_lat else lat,
            "lng": float(poi_lng) if poi_lng else lng,
            "rating": rating,
            "address": address,
            "categories": categories,
            "user_ratings_total": int(review_count) if review_count else 0,
            "photos": photos[:10] if photos else [],  # Limit to 10 photos
        }
        
        pois.append(poi)
    
    logger.info(f"Fetched {len(pois)} TripAdvisor POIs")
    return pois


if __name__ == "__main__":
    import asyncio
    
    async def main():
        async with aiohttp.ClientSession() as session:
            # Test with a location
            pois = await fetch_tripadvisor(session, 12.9716, 77.5946, "Bangalore")
            print(f"Found {len(pois)} POIs")
            for poi in pois[:3]:  # Print first 3
                print(poi)
    
    asyncio.run(main())
