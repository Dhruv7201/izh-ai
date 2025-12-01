from fastapi import APIRouter, Request
import requests
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config.database import db_config
from app.config.redis_config import redis_config
from app.config.settings import settings
import asyncio
import httpx

router = APIRouter(prefix="/health", tags=["health"])
limiter = Limiter(key_func=get_remote_address)


@router.get("")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/db")
@limiter.limit("30/minute")
async def database_health(request: Request):
    """Check database health."""
    is_healthy = await db_config.health_check()
    return {
        "database": "healthy" if is_healthy else "unhealthy",
        "status": is_healthy
    }


@router.get("/cache")
@limiter.limit("30/minute")
async def cache_health(request: Request):
    """Check Redis cache health."""
    is_healthy = await redis_config.health_check()
    return {
        "cache": "healthy" if is_healthy else "unhealthy",
        "status": is_healthy
    }


@router.get("/all")
@limiter.limit("30/minute")
async def full_health_check(request: Request):
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


@router.get("/key_check")
async def key_check():
    pass


def test_foursquare_key():
    API_KEY = settings.FOURSQUARE_API_KEY

    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Authorization": API_KEY,
    }
    params = {"query": "coffee", "near": "New York"}
    resp = requests.get(url, headers=headers, params=params)
    print("Status:", resp.status_code)
    print(resp.json())

def test_tripadvisor_key():
    API_KEY = settings.TRIPADVISOR_API_KEY

    url = f"https://api.content.tripadvisor.com/api/v1/location/search?key={API_KEY}&searchQuery=vadodara&language=en"

    headers = {"accept": "application/json"}

    response = requests.get(url, headers=headers)

    print(response.text)

def test_google_places_key():

    API_KEY = settings.GOOGLE_PLACES_API_KEY

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": "restaurants in New York",
        "key": API_KEY
    }

    resp = requests.get(url, params=params)
    print("Status:", resp.status_code)
    # print(resp.json())
