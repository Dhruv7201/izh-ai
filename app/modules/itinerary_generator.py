import sys
sys.path.append("/home/dhruv/workspace/izh/")

from app.helpers.openai_helper import openai_helper
from typing import Dict, Any, List
from app.helpers.openai_helper import ItineraryOutput


async def generate_itinerary(nlp_data: Dict[str, Any],
                             poi_data: List[Dict[str, Any]],
                             user_interests: Dict[str, float],
                             food_preferences: Dict[str, bool]) -> ItineraryOutput:
    """Generates a detailed itinerary using OpenAI based on NLP data, POI data, user interests, and food preferences."""
    return await openai_helper.generate_itinerary(nlp_data, poi_data, user_interests, food_preferences)


if __name__ == "__main__":
    import asyncio
    import time
    start = time.time()
    test_nlp_data = {
        "destination": "Amritsar",
        "duration_days": 3,
        "budget": 15000,
        "dates": "2026-01-10 to 2026-01-15",
        "trip_type": "cultural",
        "preferences": ["art", "history", "cuisine"],
    }
    test_poi_data = [
        {
            "name": "Hotel Radisson Blu",
            "distance_to_center_km": 1.2,
            "cluster_location": "Heritage Circuit",
            "opening_time": "04:00",
            "closing_time": "23:00",
            "best_time_to_visit": "early_morning"
        },
        {
            "name": "Hotel Park Plaza",
            "distance_to_center_km": 1.2,
            "cluster_location": "Heritage Circuit",
            "opening_time": "04:00",
            "closing_time": "23:00",
            "best_time_to_visit": "early_morning"
        },
        {
            "name": "Golden Temple",
            "distance_to_center_km": 1.2,
            "cluster_location": "Heritage Circuit",
            "opening_time": "04:00",
            "closing_time": "23:00",
            "best_time_to_visit": "early_morning"
        },
        {
            "name": "Hotel Radisson Blu",
            "distance_to_center_km": 1.2,
            "cluster_location": "Heritage Circuit",
            "opening_time": "04:00",
            "closing_time": "23:00",
            "best_time_to_visit": "early_morning"
        },
        {
            "name": "Jallianwala Bagh",
            "distance_to_center_km": 1.5,
            "cluster_location": "Heritage Circuit",
            "opening_time": "06:30",
            "closing_time": "19:30",
            "best_time_to_visit": "morning"
        },
        {
            "name": "Partition Museum",
            "distance_to_center_km": 1.6,
            "cluster_location": "Heritage Circuit",
            "opening_time": "10:00",
            "closing_time": "18:00",
            "best_time_to_visit": "afternoon"
        },
        {
            "name": "Wagah Border Ceremony",
            "distance_to_center_km": 30.0,
            "cluster_location": "Outskirts",
            "opening_time": "15:00",
            "closing_time": "18:00",
            "best_time_to_visit": "evening"
        },
        {
            "name": "Gobindgarh Fort",
            "distance_to_center_km": 2.5,
            "cluster_location": "Central",
            "opening_time": "10:00",
            "closing_time": "22:00",
            "best_time_to_visit": "evening"
        },
        {
            "name": "Durgiana Temple",
            "distance_to_center_km": 2.0,
            "cluster_location": "Central",
            "opening_time": "05:00",
            "closing_time": "21:00",
            "best_time_to_visit": "morning"
        },
        {
            "name": "Hall Bazaar",
            "distance_to_center_km": 1.0,
            "cluster_location": "Marketplace",
            "opening_time": "10:00",
            "closing_time": "22:00",
            "best_time_to_visit": "afternoon"
        },
        {
            "name": "Khalsa College",
            "distance_to_center_km": 5.0,
            "cluster_location": "Academic Belt",
            "opening_time": "09:00",
            "closing_time": "17:00",
            "best_time_to_visit": "morning"
        },
        {
            "name": "Ram Tirath Temple",
            "distance_to_center_km": 12.0,
            "cluster_location": "Outskirts",
            "opening_time": "06:00",
            "closing_time": "20:00",
            "best_time_to_visit": "morning"
        },
        {
            "name": "Sadda Pind",
            "distance_to_center_km": 8.0,
            "cluster_location": "Experience Zone",
            "opening_time": "11:00",
            "closing_time": "23:00",
            "best_time_to_visit": "evening"
    }]
    test_user_interests = {
        "cultural_trip": 0.40,
        "food_trip": 0.25,
        "heritage_trip": 0.20,
        "shopping_trip": 0.10,
        "relaxation_trip": 0.05
    }

    food_preferences = {
        "vegetarian": True,
        "spicy_food": True,
        "street_food": True,
        "local_cuisine": True,
        "fine_dining": False
    }


    result = asyncio.run(generate_itinerary(test_nlp_data, test_poi_data, test_user_interests, food_preferences))

    print(type(result))
    print(result.model_dump_json(indent=2))
    print("Time taken:", time.time() - start)