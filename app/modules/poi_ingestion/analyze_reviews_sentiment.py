

import sys
sys.path.append("/home/dhruv/workspace/izh")
import asyncio
import logging
from app.config.database import db_config
from app.modules.poi_ingestion.sentiment_analysis import (
    analyze_all_reviews,
    analyze_reviews_by_poi_id,
    get_average_sentiment_by_poi_id
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to analyze sentiment for all reviews."""
    try:
        # Ensure database is connected
        if not db_config._initialized:
            await db_config.connect()
        
        logger.info("Starting sentiment analysis for all reviews...")
        
        # Analyze all reviews without sentiment scores
        result = await analyze_all_reviews(batch_size=100)
        
        logger.info(f"Analysis complete:")
        logger.info(f"  Total reviews processed: {result.get('total_reviews', 0)}")
        logger.info(f"  Successfully analyzed: {result.get('analyzed', 0)}")
        logger.info(f"  Failed: {result.get('failed', 0)}")
        
        if 'error' in result:
            logger.error(f"Error occurred: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        # Don't disconnect if using connection pooling
        # The connection pool will be managed by the application lifecycle
        pass


async def analyze_specific_poi(poi_id: int):
    """Analyze sentiment for reviews of a specific POI."""
    try:
        if not db_config._initialized:
            await db_config.connect()
        
        logger.info(f"Analyzing sentiment for POI ID {poi_id}...")
        
        result = await analyze_reviews_by_poi_id(poi_id)
        logger.info(f"Analysis complete for POI {poi_id}:")
        logger.info(f"  Total reviews: {result.get('total_reviews', 0)}")
        logger.info(f"  Analyzed: {result.get('analyzed', 0)}")
        logger.info(f"  Failed: {result.get('failed', 0)}")
        
        # Get average sentiment
        avg_sentiment = await get_average_sentiment_by_poi_id(poi_id)
        if avg_sentiment:
            logger.info(f"  Average sentiment score: {avg_sentiment:.2f}/10")
        
    except Exception as e:
        logger.error(f"Error analyzing POI {poi_id}: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze sentiment for reviews')
    parser.add_argument(
        '--poi-id',
        type=int,
        help='Analyze reviews for a specific POI ID (optional)'
    )
    
    args = parser.parse_args()
    
    if args.poi_id:
        asyncio.run(analyze_specific_poi(args.poi_id))
    else:
        asyncio.run(main())

