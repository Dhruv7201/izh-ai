from fastapi import APIRouter

from app.config.database import db_config
from app.config.redis_config import redis_config

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/db")
async def database_health():
    """Check database health."""
    is_healthy = await db_config.health_check()
    return {
        "database": "healthy" if is_healthy else "unhealthy",
        "status": is_healthy
    }


@router.get("/cache")
async def cache_health():
    """Check Redis cache health."""
    is_healthy = await redis_config.health_check()
    return {
        "cache": "healthy" if is_healthy else "unhealthy",
        "status": is_healthy
    }


@router.get("/all")
async def full_health_check():
    """Check all services."""
    db_healthy = await db_config.health_check()
    cache_healthy = await redis_config.health_check()
    
    return {
        "status": "healthy" if (db_healthy and cache_healthy) else "degraded",
        "services": {
            "database": db_healthy,
            "cache": cache_healthy,
        }
    }
