import uuid
import json

def normalize(raw):
    """Normalize raw POI data into basic POI and details structure."""
    poi_uuid = str(uuid.uuid4())
    
    # Basic POI data (for pois table)
    poi_data = {
        "poi_uuid": poi_uuid,
        "source": raw["source"],
        "source_id": str(raw["id"]) if raw.get("id") else None,
        "name": raw["name"],
        "lat": float(raw["lat"]),
        "lng": float(raw["lng"]),
        "rating": float(raw.get("rating", 0)) if raw.get("rating") else None,
        "address": raw.get("address"),
    }
    
    # Details data (for poi_details table)
    details_data = {
        "categories": extract_categories(raw),
        "opening_hours": raw.get("opening_hours", []),
        "duration_minutes": estimate_duration(raw),
        "best_time": estimate_best_time(raw),
        "photos": raw.get("photos", []),
        "user_ratings_total": raw.get("user_ratings_total", 0),
    }
    
    return {
        "poi": poi_data,
        "details": details_data
    }

def extract_categories(p):
    if p["source"] == "google":
        return p.get("types", [])
    if p["source"] == "foursquare":
        return p.get("categories", [])
    if p["source"] == "tripadvisor":
        return p.get("categories", [])
    return []

def estimate_duration(p):
    cats = str(p)
    if "museum" in cats: return 120
    if "restaurant" in cats: return 60
    if "park" in cats: return 150
    return 90

def estimate_best_time(p):
    name = p["name"].lower()
    if "sunset" in name or "beach" in name: return ["evening"]
    if "temple" in name or "church" in name: return ["morning"]
    return ["any"]
