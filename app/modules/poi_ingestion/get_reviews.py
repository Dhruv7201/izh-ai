import sys
sys.path.append("/home/dhruv/workspace/izh")
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from app.helpers.db_executor import query_executor
from app.modules.poi_ingestion.sentiment_analysis import analyze_sentiment
from app.config.settings import settings

logger = logging.getLogger(__name__)


async def store_reviews(poi_id: int, reviews: List[Dict[str, Any]]) -> int:
    """
    Store reviews for a POI in the poi_reviews table.
    
    Args:
        poi_id: The ID of the POI in the pois table
        reviews: List of review dictionaries from Google Places API
        
    Returns:
        Number of reviews stored (including updates)
    """
    if not reviews:
        logger.debug(f"No reviews to store for POI ID {poi_id}")
        return 0
    
    stored_count = 0
    
    for review in reviews:
        try:
            # Extract review fields (handle optional fields)
            author_name = review.get("author_name")
            author_url = review.get("author_url")
            language = review.get("language")
            profile_photo_url = review.get("profile_photo_url")
            rating = review.get("rating")
            relative_time_description = review.get("relative_time_description")
            text = review.get("text")
            time = review.get("time")
            
            # Skip if essential fields are missing
            if not author_name or not text:
                logger.warning(f"Skipping review for POI {poi_id}: missing author_name or text")
                continue
            
            # Analyze sentiment for the review text
            sentiment_score = analyze_sentiment(text)
            
            # Insert or update review (using ON CONFLICT to handle duplicates)
            insert_query = """
                INSERT INTO poi_reviews (
                    poi_id, author_name, author_url, language,
                    profile_photo_url, rating, relative_time_description,
                    text, time, sentiment_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (poi_id, author_name, time) DO UPDATE SET
                    author_url = EXCLUDED.author_url,
                    language = EXCLUDED.language,
                    profile_photo_url = EXCLUDED.profile_photo_url,
                    rating = EXCLUDED.rating,
                    relative_time_description = EXCLUDED.relative_time_description,
                    text = EXCLUDED.text,
                    sentiment_score = EXCLUDED.sentiment_score
            """
            
            await query_executor.execute(
                insert_query,
                poi_id,
                author_name,
                author_url,
                language,
                profile_photo_url,
                rating,
                relative_time_description,
                text,
                time,
                sentiment_score
            )
            
            stored_count += 1
            
        except Exception as e:
            logger.error(f"Error storing review for POI {poi_id}: {e}")
            continue
    
    logger.info(f"Stored {stored_count} reviews for POI ID {poi_id}")
    return stored_count


async def get_reviews_by_poi_id(poi_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve all reviews for a specific POI.
    
    Args:
        poi_id: The ID of the POI in the pois table
        
    Returns:
        List of review dictionaries
    """
    query = """
        SELECT 
            id, poi_id, author_name, author_url, language,
            profile_photo_url, rating, relative_time_description,
            text, time, sentiment_score, created_at
        FROM poi_reviews
        WHERE poi_id = $1
        ORDER BY time DESC, rating DESC
    """
    
    reviews = await query_executor.fetch_all(query, poi_id)
    return reviews


async def get_reviews_by_source_id(source: str, source_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all reviews for a POI by source and source_id.
    First finds the POI, then retrieves its reviews.
    
    Args:
        source: The source of the POI (e.g., 'google')
        source_id: The source ID (e.g., place_id from Google)
        
    Returns:
        List of review dictionaries
    """
    # First, get the POI ID
    poi_query = "SELECT id FROM pois WHERE source = $1 AND source_id = $2"
    poi = await query_executor.fetch_one(poi_query, source, source_id)
    
    if not poi:
        logger.warning(f"POI not found for source={source}, source_id={source_id}")
        return []
    
    return await get_reviews_by_poi_id(poi["id"])


async def fetch_tripadvisor_reviews(session: aiohttp.ClientSession, location_id: str, language: str = "en") -> List[Dict[str, Any]]:
    """
    Fetch reviews from TripAdvisor API for a given location ID.
    
    Args:
        session: aiohttp ClientSession
        location_id: TripAdvisor location ID
        language: Language code (default: "en")
        
    Returns:
        List of review dictionaries with normalized structure
    """
    url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/reviews"
    params = {
        "language": language,
        "key": settings.TRIPADVISOR_API_KEY
    }
    
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"TripAdvisor reviews API failed with status {resp.status} for location {location_id}")
                return []
            
            data = await resp.json()
            # Handle different response structures
            reviews_data = data.get("data", [])
            if not reviews_data and isinstance(data, list):
                reviews_data = data
            
            # Normalize TripAdvisor reviews to match Google Places format
            normalized_reviews = []
            for review in reviews_data:
                if not isinstance(review, dict):
                    continue
                
                # Extract user information
                user = review.get("user", {})
                if not isinstance(user, dict):
                    user = {}
                
                # Extract avatar/photo URL
                avatar = user.get("avatar", {}) if isinstance(user.get("avatar"), dict) else {}
                thumbnail = avatar.get("thumbnail", {}) if isinstance(avatar.get("thumbnail"), dict) else {}
                photo_url = thumbnail.get("url") or avatar.get("url") or user.get("avatar")
                
                # Extract text (try multiple possible fields)
                text = review.get("text") or review.get("reviewText") or review.get("review_text") or ""
                
                # Extract rating (handle different formats)
                rating = review.get("rating")
                if isinstance(rating, dict):
                    rating = rating.get("rating") or rating.get("value")
                rating = float(rating) if rating else 0
                
                # Extract date/time
                date_value = review.get("publishedDate") or review.get("date") or review.get("published_date")
                
                normalized_review = {
                    "source": "tripadvisor",
                    "author_name": user.get("username") or review.get("username") or "Anonymous",
                    "author_url": photo_url,
                    "language": language,
                    "profile_photo_url": photo_url,
                    "rating": rating,
                    "relative_time_description": date_value,
                    "text": text,
                    "time": date_value,
                    "title": review.get("title")
                }
                
                # Skip if essential fields are missing
                if normalized_review.get("text"):
                    normalized_reviews.append(normalized_review)
            
            logger.info(f"Fetched {len(normalized_reviews)} TripAdvisor reviews for location {location_id}")
            return normalized_reviews
            
    except Exception as e:
        logger.error(f"Error fetching TripAdvisor reviews for location {location_id}: {e}")
        return []


async def fetch_google_places_reviews(session: aiohttp.ClientSession, place_id: str) -> List[Dict[str, Any]]:
    """
    Fetch reviews from Google Places API for a given place ID.
    
    Args:
        session: aiohttp ClientSession
        place_id: Google Places place_id
        
    Returns:
        List of review dictionaries
    """
    if not place_id or not place_id.strip():
        logger.warning("Empty or None place_id provided to fetch_google_places_reviews")
        return []
    
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id.strip(),
        "key": settings.GOOGLE_PLACES_API_KEY,
        "fields": "name,rating,user_ratings_total,reviews",
        "language": "en"
    }
    
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"Google Places API failed with status {resp.status} for place {place_id}")
                return []
            
            data = await resp.json()
            
            # Check for API errors
            status = data.get("status")
            if status != "OK":
                error_message = data.get("error_message", "Unknown error")
                logger.error(f"Google Places API error (status: {status}): {error_message} for place_id: {place_id}")
                return []

            result = data.get("result", {})
            reviews = result.get("reviews", [])

            # Add source identifier
            for review in reviews:
                review["source"] = "google"

            logger.info(f"Fetched {len(reviews)} Google Places reviews for place {place_id}")
            return reviews
            
    except Exception as e:
        logger.error(f"Error fetching Google Places reviews for place {place_id}: {e}")
        return []


async def fetch_combined_reviews(
    session: aiohttp.ClientSession,
    google_place_id: Optional[str] = None,
    tripadvisor_location_id: Optional[str] = None,
    language: str = "en"
) -> List[Dict[str, Any]]:
    """
    Fetch and combine reviews from both Google Places and TripAdvisor.
    
    Args:
        session: aiohttp ClientSession
        google_place_id: Optional Google Places place_id
        tripadvisor_location_id: Optional TripAdvisor location_id
        language: Language code for TripAdvisor (default: "en")
        
    Returns:
        Combined list of review dictionaries from both sources
    """
    all_reviews = []
    
    # Fetch Google Places reviews if place_id is provided
    if google_place_id:
        google_reviews = await fetch_google_places_reviews(session, google_place_id)
        all_reviews.extend(google_reviews)
    
    # Fetch TripAdvisor reviews if location_id is provided
    if tripadvisor_location_id:
        tripadvisor_reviews = await fetch_tripadvisor_reviews(session, tripadvisor_location_id, language)
        all_reviews.extend(tripadvisor_reviews)
    
    logger.info(f"Combined {len(all_reviews)} reviews from all sources")
    return all_reviews


async def analyze_reviews_sentiment_without_storage(
    session: aiohttp.ClientSession,
    google_place_id: Optional[str] = None,
    tripadvisor_location_id: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Fetch reviews from Google Places and/or TripAdvisor, analyze sentiment,
    and return results without storing in the database.
    
    Args:
        session: aiohttp ClientSession
        google_place_id: Optional Google Places place_id
        tripadvisor_location_id: Optional TripAdvisor location_id
        language: Language code for TripAdvisor (default: "en")
        
    Returns:
        Dictionary containing:
        - reviews: List of reviews with sentiment scores
        - statistics: Summary statistics (total, average_sentiment, etc.)
    """
    # Fetch combined reviews
    reviews = await fetch_combined_reviews(
        session,
        google_place_id=google_place_id,
        tripadvisor_location_id=tripadvisor_location_id,
        language=language
    )
    
    if not reviews:
        return {
            "reviews": [],
            "statistics": {
                "total_reviews": 0,
                "average_sentiment": None,
                "average_rating": None,
                "sources": {}
            }
        }
    
    # Analyze sentiment for each review
    analyzed_reviews = []
    sentiment_scores = []
    ratings = []
    source_counts = {}
    
    for review in reviews:
        text = review.get("text", "")
        if not text:
            continue
        
        # Analyze sentiment
        sentiment_score = analyze_sentiment(text)
        
        # Add sentiment to review
        review_with_sentiment = review.copy()
        review_with_sentiment["sentiment_score"] = sentiment_score
        
        analyzed_reviews.append(review_with_sentiment)
        sentiment_scores.append(sentiment_score)
        
        # Collect rating if available
        rating = review.get("rating")
        if rating:
            ratings.append(float(rating))
        
        # Count by source
        source = review.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    
    # Calculate statistics
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    
    statistics = {
        "total_reviews": len(analyzed_reviews),
        "average_sentiment": round(avg_sentiment, 2) if avg_sentiment else None,
        "average_rating": round(avg_rating, 2) if avg_rating else None,
        "sources": source_counts,
        "sentiment_range": {
            "min": round(min(sentiment_scores), 2) if sentiment_scores else None,
            "max": round(max(sentiment_scores), 2) if sentiment_scores else None
        }
    }
    
    logger.info(
        f"Analyzed {len(analyzed_reviews)} reviews: "
        f"avg_sentiment={statistics['average_sentiment']}, "
        f"avg_rating={statistics['average_rating']}"
    )
    
    return {
        "reviews": analyzed_reviews,
        "statistics": statistics
    }


