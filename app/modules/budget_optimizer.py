import re
from typing import Dict, Any, Optional, Tuple
from app.helpers.openai_helper import ItineraryOutput, MultipleItinerariesOutput


def parse_budget(budget_str: Optional[str]) -> Optional[float]:
    """Parse budget string like '₹20000' to numeric value."""
    if not budget_str:
        return None
    
    # Extract numeric value from string like "₹20000" or "20000"
    match = re.search(r"(\d+(?:\.\d+)?)", str(budget_str))
    if match:
        return float(match.group(1))
    return None


def calculate_itinerary_cost(
    itinerary: ItineraryOutput,
    duration_days: Optional[int],
    daily_food_cost: float = 2000.0,
    daily_activity_cost: float = 1500.0,
    daily_transport_cost: float = 500.0
) -> float:
    """
    Calculate total estimated cost for an itinerary.
    
    Args:
        itinerary: The itinerary to calculate cost for
        duration_days: Number of days for the trip
        daily_food_cost: Estimated daily food cost per person (default: ₹2000)
        daily_activity_cost: Estimated daily activity/entertainment cost (default: ₹1500)
        daily_transport_cost: Estimated daily transport cost (default: ₹500)
    
    Returns:
        Total estimated cost in rupees
    """
    total_cost = 0.0
    
    # Calculate hotel cost (use cheapest hotel or first hotel if available)
    if itinerary.hotels:
        # Use the cheapest hotel price
        cheapest_hotel_price = min(hotel.price_per_night for hotel in itinerary.hotels)
        # Number of nights = duration_days - 1 (or duration_days if same day return)
        nights = duration_days - 1 if duration_days and duration_days > 1 else 1
        total_cost += cheapest_hotel_price * nights
    else:
        # Default hotel cost if no hotels provided
        nights = duration_days - 1 if duration_days and duration_days > 1 else 1
        total_cost += 3000 * nights  # Default ₹3000 per night
    
    # Calculate daily costs (food, activities, transport)
    days = duration_days if duration_days else len(itinerary.day_plans)
    total_cost += (daily_food_cost + daily_activity_cost + daily_transport_cost) * days
    
    return total_cost
