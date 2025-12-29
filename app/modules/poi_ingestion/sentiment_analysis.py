import sys
sys.path.append("/home/dhruv/workspace/izh")
import logging
from typing import Optional, Dict, Any, List
from textblob import TextBlob
import asyncio

from app.helpers.db_executor import query_executor

logger = logging.getLogger(__name__)


def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of a review text and return a score from 0 to 10.
    
    Args:
        text: The review text to analyze
        
    Returns:
        Sentiment score from 0.0 (most negative) to 10.0 (most positive)
    """
    if not text or not text.strip():
        return 5.0  # Neutral score for empty text
    
    try:
        # TextBlob returns polarity between -1 (negative) and 1 (positive)
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Convert from [-1, 1] to [0, 10] scale
        # polarity -1 -> 0, polarity 0 -> 5, polarity 1 -> 10
        sentiment_score = ((polarity + 1) / 2) * 10
        
        # Round to 2 decimal places
        return round(sentiment_score, 2)
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment for text: {e}")
        return 5.0  # Return neutral score on error


async def update_review_sentiment(review_id: int, sentiment_score: float) -> bool:
    """
    Update a single review with its sentiment score.
    
    Args:
        review_id: The ID of the review
        sentiment_score: The sentiment score (0-10)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
            UPDATE poi_reviews
            SET sentiment_score = $1
            WHERE id = $2
        """
        await query_executor.execute(query, sentiment_score, review_id)
        return True
    except Exception as e:
        logger.error(f"Error updating sentiment for review {review_id}: {e}")
        return False


async def analyze_and_update_review(review_id: int, text: str) -> Optional[float]:
    """
    Analyze sentiment of a review and update the database.
    
    Args:
        review_id: The ID of the review
        text: The review text
        
    Returns:
        The sentiment score if successful, None otherwise
    """
    sentiment_score = analyze_sentiment(text)
    success = await update_review_sentiment(review_id, sentiment_score)
    
    if success:
        return sentiment_score
    return None


async def analyze_reviews_by_poi_id(poi_id: int, batch_size: int = 50) -> Dict[str, Any]:
    """
    Analyze sentiment for all reviews of a specific POI that don't have sentiment scores yet.
    
    Args:
        poi_id: The ID of the POI
        batch_size: Number of reviews to process in each batch
        
    Returns:
        Dictionary with statistics about the analysis
    """
    try:
        # Get reviews without sentiment scores
        query = """
            SELECT id, text
            FROM poi_reviews
            WHERE poi_id = $1 AND (sentiment_score IS NULL OR sentiment_score = 0)
            ORDER BY id
        """
        reviews = await query_executor.fetch_all(query, poi_id)
        
        if not reviews:
            logger.info(f"No reviews to analyze for POI ID {poi_id}")
            return {
                "poi_id": poi_id,
                "total_reviews": 0,
                "analyzed": 0,
                "failed": 0
            }
        
        analyzed_count = 0
        failed_count = 0
        
        # Process reviews in batches
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                analyze_and_update_review(review["id"], review["text"])
                for review in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing review: {result}")
                    failed_count += 1
                elif result is not None:
                    analyzed_count += 1
                else:
                    failed_count += 1
        
        logger.info(
            f"Analyzed sentiment for POI ID {poi_id}: "
            f"{analyzed_count} succeeded, {failed_count} failed out of {len(reviews)} reviews"
        )
        
        return {
            "poi_id": poi_id,
            "total_reviews": len(reviews),
            "analyzed": analyzed_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"Error analyzing reviews for POI ID {poi_id}: {e}")
        return {
            "poi_id": poi_id,
            "total_reviews": 0,
            "analyzed": 0,
            "failed": 0,
            "error": str(e)
        }


async def analyze_all_reviews(batch_size: int = 100) -> Dict[str, Any]:
    """
    Analyze sentiment for all reviews in the database that don't have sentiment scores yet.
    
    Args:
        batch_size: Number of reviews to process in each batch
        
    Returns:
        Dictionary with overall statistics
    """
    try:
        # Get all reviews without sentiment scores
        query = """
            SELECT id, text, poi_id
            FROM poi_reviews
            WHERE sentiment_score IS NULL OR sentiment_score = 0
            ORDER BY poi_id, id
        """
        reviews = await query_executor.fetch_all(query)
        
        if not reviews:
            logger.info("No reviews to analyze")
            return {
                "total_reviews": 0,
                "analyzed": 0,
                "failed": 0
            }
        
        analyzed_count = 0
        failed_count = 0
        
        # Process reviews in batches
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                analyze_and_update_review(review["id"], review["text"])
                for review in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                elif result is not None:
                    analyzed_count += 1
                else:
                    failed_count += 1
            
            logger.info(
                f"Progress: {min(i + batch_size, len(reviews))}/{len(reviews)} reviews processed"
            )
        
        logger.info(
            f"Completed sentiment analysis: "
            f"{analyzed_count} succeeded, {failed_count} failed out of {len(reviews)} reviews"
        )
        
        return {
            "total_reviews": len(reviews),
            "analyzed": analyzed_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"Error analyzing all reviews: {e}")
        return {
            "total_reviews": 0,
            "analyzed": 0,
            "failed": 0,
            "error": str(e)
        }


async def get_average_sentiment_by_poi_id(poi_id: int) -> Optional[float]:
    """
    Get the average sentiment score for all reviews of a specific POI.
    
    Args:
        poi_id: The ID of the POI
        
    Returns:
        Average sentiment score (0-10) or None if no reviews with sentiment scores exist
    """
    try:
        query = """
            SELECT AVG(sentiment_score) as avg_sentiment
            FROM poi_reviews
            WHERE poi_id = $1 AND sentiment_score IS NOT NULL
        """
        result = await query_executor.fetch_one(query, poi_id)
        
        if result and result.get("avg_sentiment"):
            return round(float(result["avg_sentiment"]), 2)
        return None
        
    except Exception as e:
        logger.error(f"Error getting average sentiment for POI ID {poi_id}: {e}")
        return None

