"""
Scheduler for monthly POI ingestion.

This module provides functionality to schedule and run monthly POI ingestion.
Can be used with:
1. APScheduler (background task scheduler)
2. Cron jobs (system-level scheduling)
3. Manual execution
"""

import asyncio
import logging
from datetime import date
from typing import List, Tuple

from app.config.database import db_config
from app.modules.poi_ingestion.ingest import ingest_destination

logger = logging.getLogger(__name__)


async def run_monthly_ingestion(destinations: List[Tuple[str, float, float]]):
    """
    Run monthly ingestion for all specified destinations.
    
    Args:
        destinations: List of tuples (name, lat, lng) for each destination
    """
    ingestion_date = date.today()
    logger.info(f"Starting monthly POI ingestion on {ingestion_date}")
    logger.info(f"Processing {len(destinations)} destination(s)")
    
    # Ensure database is connected
    if not db_config._initialized:
        await db_config.connect()
    
    try:
        # Process all destinations concurrently
        coros = [
            ingest_destination(name, lat, lng, ingestion_date) 
            for name, lat, lng in destinations
        ]
        await asyncio.gather(*coros)
        
        logger.info("✅ Monthly ingestion process completed successfully")
    except Exception as e:
        logger.error(f"❌ Error during monthly ingestion: {e}", exc_info=True)
        raise
    finally:
        # Note: Don't disconnect if using connection pooling
        # The connection pool will be managed by the application lifecycle
        pass


def get_destinations_from_config() -> List[Tuple[str, float, float]]:
    """
    Get destinations from configuration.
    This can be extended to read from a database, config file, or environment variables.
    
    Returns:
        List of tuples (name, lat, lng)
    """
    # TODO: Load from database or config file
    # For now, return hardcoded list
    return [
        # ("golden temple", 31.6200, 74.8765),
        ("vadodara", 22.3072, 73.1812),
    ]


async def scheduled_ingestion():
    """
    Scheduled ingestion function that can be called by APScheduler or cron.
    """
    destinations = get_destinations_from_config()
    await run_monthly_ingestion(destinations)


if __name__ == "__main__":
    # For manual execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    destinations = get_destinations_from_config()
    asyncio.run(run_monthly_ingestion(destinations))

