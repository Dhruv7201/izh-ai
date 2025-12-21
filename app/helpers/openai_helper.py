import os
import logging
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from app.config.settings import settings
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from toon import encode

logger = logging.getLogger(__name__)


class Activity(BaseModel):
    time: str
    title: str
    description: Optional[str]
    poi: Optional[str]  # must match POI name from poi_data when used


class DayPlan(BaseModel):
    day: int
    date: Optional[str]
    summary: Optional[str]
    activities: List[Activity]


class HotelRecommendation(BaseModel):
    name: str
    location: str
    rating: float
    price_per_night: int
    distance_to_center_km: float
    reasons: List[str]


class ItineraryOutput(BaseModel):
    destination: str
    summary: str
    hotels: List[HotelRecommendation]
    day_plans: List[DayPlan]


class MultipleItinerariesOutput(BaseModel):
    itineraries: List[ItineraryOutput]


os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

llm = OpenAIModel(settings.OPENAI_MODEL)

# The KEY — this is the correct structured-output way
itinerary_agent = Agent(
    llm,
    output_type=MultipleItinerariesOutput,
)


class OpenAIHelper:

    async def generate_itinerary(
        self,
        nlp_data: Dict[str, Any],
        poi_data: List[Dict[str, Any]],
        user_interests: Dict[str, float],
        food_preferences: Dict[str, bool]
    ) -> MultipleItinerariesOutput:
            
        """Generates a detailed itinerary using OpenAI based on NLP data, POI data, user interests, and food preferences."""

        encoded_nlp_data = encode(nlp_data)
        encoded_poi_data = encode(poi_data)
        encoded_user_interests = encode(user_interests)
        encoded_food_preferences = encode(food_preferences)
        print("Encoded NLP Data:", encoded_nlp_data)
        print("Encoded POI Data:", encoded_poi_data)
        print("Encoded User Interests:", encoded_user_interests)
        print("Encoded Food Preferences:", encoded_food_preferences)

        prompt = f"""
        Produce MULTIPLE itinerary OPTIONS using the exact schema below.

        Return exactly 3 different itineraries inside an array called `itineraries`.

        Each itinerary should:
        - Have a different style (e.g. relaxed, romantic, adventurous)
        - Still follow ALL rules below

        Schema:

        itineraries: list of {{
            destination: str
            summary: str
            hotels: list of {{
                name: str,
                location: str,
                rating: float,
                price_per_night: int,
                distance_to_center_km: float,
                reasons: list[str]
            }}
            day_plans: list of {{
                day: int,
                date: str | null,
                summary: str | null,
                activities: list[{{ 
                    time: str, 
                    title: str, 
                    description: str | null, 
                    poi: str | null 
                }}]
            }}
        }}

        Rules and constraints:
        - Provide EXACTLY 3 itineraries
        - Each itinerary must feel meaningfully different
        - Give 3 hotel recommendations per itinerary
        - Use ONLY POIs from the POI_DATA array for `poi`
        - If activity is generic, set `poi` to null
        - Respect POI opening_time and closing_time
        - Prefer best_time_to_visit when possible
        - Use USER_INTERESTS for prioritization
        - Balance sightseeing, meals, rest, and travel

        NLP_DATA:
        {encoded_nlp_data}

        POI_DATA:
        {encoded_poi_data}

        USER_INTERESTS:
        {encoded_user_interests}
        """

        result = await itinerary_agent.run(prompt)
        return result.output


openai_helper = OpenAIHelper()
