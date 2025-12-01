import uuid

def normalize(raw):
    return {
        "poi_uuid": str(uuid.uuid4()),
        "source": raw["source"],
        "source_id": raw["id"],
        "name": raw["name"],
        "lat": raw["lat"],
        "lng": raw["lng"],
        "rating": raw.get("rating", 0),
        "address": raw.get("address"),
        "categories": extract_categories(raw),
        "opening_hours": raw.get("opening_hours", []),
        "duration_minutes": estimate_duration(raw),
        "best_time": estimate_best_time(raw),
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
