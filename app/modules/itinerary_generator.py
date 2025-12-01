import asyncio
from typing import Dict, Any, List

from app.modules.weather import get_weather_categories
from app.helpers.openai_helper import openai_helper



def generate_time_slots(energy_level: str) -> List[str]:
    """4 time-slots per day always."""
    templates = {
        "high": ["8–10 AM", "11 AM–1 PM", "3–5 PM", "7–9 PM"],
        "medium": ["9–11 AM", "12–2 PM", "4–6 PM", "7–9 PM"],
        "low": ["10–12 AM", "1–3 PM", "4–6 PM", "6–8 PM"],
    }
    return templates.get(energy_level, templates["medium"])


def get_nearby_pois(destination: str, interests: List[str]) -> List[Dict[str, Any]]:
    """
    Dummy now → can be replaced with DB/API results.
    """
    pois = [
        {"name": "Sunset Beach", "category": "Romantic", "cluster_id": 1, "lat": 1, "lng": 1},
        {"name": "Nightlife Strip", "category": "Nightlife", "cluster_id": 1, "lat": 1.1, "lng": 1.1},
        {"name": "Water Sports Bay", "category": "Adventure", "cluster_id": 2, "lat": 2, "lng": 2},
        {"name": "Fort Aguada", "category": "History", "cluster_id": 3, "lat": 3, "lng": 3},
    ]

    return [p for p in pois if p["category"].lower() in [i.lower() for i in interests]]


def structure_itinerary(days: int, slots: List[str], pois: List[Dict[str, Any]]):
    """
    Assign 4 POIs per day, based on clusters (nearby itineraries)
    """
    itinerary = {}

    poi_cycle = pois * days  # repeat POIs if needed
    idx = 0

    for d in range(1, days + 1):
        day_key = f"day_{d}"
        itinerary[day_key] = []

        for slot in slots:
            if idx < len(poi_cycle):
                itinerary[day_key].append({
                    "time_slot": slot,
                    "poi": poi_cycle[idx],
                    "type": poi_cycle[idx]["category"]
                })
            idx += 1

    return itinerary


async def generate_itinerary_text(nlp_data: Dict[str, Any]):
    destination = nlp_data.get("destination")
    days = nlp_data.get("duration_days", 3)
    budget = nlp_data.get("budget")
    interests = nlp_data.get("interests", [])
    activities = nlp_data.get("activities", [])
    energy_level = nlp_data.get("energy_level", "medium")

    # 1. Time Slots (4 per day)
    slots = generate_time_slots(energy_level)

    # 2. POIs (filtered by interests)
    pois = get_nearby_pois(destination, interests)

    # 3. Weather
    weather_data = get_weather_categories(destination)

    # 4. Structure itinerary
    itinerary_plan = structure_itinerary(days, slots, pois)

    # 5. LLM generation
    payload = {
        "destination": destination,
        "days": days,
        "budget": budget,
        "interests": interests,
        "activities": activities,
        "slots": slots,
        "weather": weather_data,
        "day_plan": itinerary_plan,
    }

    response = await openai_helper.chat_completion(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Generate a user-friendly multi-day itinerary."},
            {"role": "user", "content": str(payload)},
        ]
    )

    return response.choices[0].message.content
