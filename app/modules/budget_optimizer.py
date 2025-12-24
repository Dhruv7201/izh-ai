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


def select_best_itinerary_for_budget(
    multiple_itineraries: MultipleItinerariesOutput,
    budget: Optional[str],
    duration_days: Optional[int],
    daily_food_cost: float = 2000.0,
    daily_activity_cost: float = 1500.0,
    daily_transport_cost: float = 500.0
) -> Tuple[ItineraryOutput, bool]:
    """
    Select the best itinerary from multiple options based on budget constraints.
    
    Args:
        multiple_itineraries: Multiple itinerary options to choose from
        budget: Budget string from NLP (e.g., "₹20000")
        duration_days: Number of days for the trip
        daily_food_cost: Estimated daily food cost per person (default: ₹2000)
        daily_activity_cost: Estimated daily activity/entertainment cost (default: ₹1500)
        daily_transport_cost: Estimated daily transport cost (default: ₹500)
    
    Returns:
        Tuple of (selected_itinerary, best_for_budget_flag)
        - selected_itinerary: The itinerary that best fits the budget
        - best_for_budget: True if the selected itinerary fits within budget, False otherwise
    """
    if not multiple_itineraries.itineraries:
        raise ValueError("No itineraries provided")
    
    # Parse budget to numeric value
    budget_value = parse_budget(budget)
    
    # Calculate cost for each itinerary
    itinerary_costs = []
    for itinerary in multiple_itineraries.itineraries:
        cost = calculate_itinerary_cost(
            itinerary,
            duration_days,
            daily_food_cost,
            daily_activity_cost,
            daily_transport_cost
        )
        itinerary_costs.append((itinerary, cost))
    
    # If no budget specified, return the cheapest itinerary
    if budget_value is None:
        cheapest = min(itinerary_costs, key=lambda x: x[1])
        return cheapest[0], False
    
    # Filter itineraries that fit within budget
    within_budget = [
        (itinerary, cost) for itinerary, cost in itinerary_costs
        if cost <= budget_value
    ]
    
    if within_budget:
        # Select the one closest to budget (most value for money)
        # Prefer the one with highest cost that's still within budget
        best_itinerary, best_cost = max(within_budget, key=lambda x: x[1])
        return best_itinerary, True
    else:
        # No itinerary fits within budget, return the cheapest one
        cheapest = min(itinerary_costs, key=lambda x: x[1])
        return cheapest[0], False


def optimize_budget(
    multiple_itineraries: MultipleItinerariesOutput,
    nlp_data: Dict[str, Any],
    daily_food_cost: float = 2000.0,
    daily_activity_cost: float = 1500.0,
    daily_transport_cost: float = 500.0
) -> Dict[str, Any]:
    """
    Main entry point for budget optimization.
    Selects the best itinerary from multiple options based on budget from NLP data.
    
    Args:
        multiple_itineraries: Multiple itinerary options to choose from
        nlp_data: NLP parsed data containing budget and duration_days
        daily_food_cost: Estimated daily food cost per person (default: ₹2000)
        daily_activity_cost: Estimated daily activity/entertainment cost (default: ₹1500)
        daily_transport_cost: Estimated daily transport cost (default: ₹500)
    
    Returns:
        Dictionary containing:
        - itinerary: The selected itinerary (ItineraryOutput)
        - best_for_budget: Boolean flag indicating if it fits within budget
        - estimated_cost: Total estimated cost of the selected itinerary
        - budget: The user's budget (if provided)
    """
    budget = nlp_data.get("budget")
    duration_days = nlp_data.get("duration_days")
    
    selected_itinerary, best_for_budget = select_best_itinerary_for_budget(
        multiple_itineraries,
        budget,
        duration_days,
        daily_food_cost,
        daily_activity_cost,
        daily_transport_cost
    )
    
    estimated_cost = calculate_itinerary_cost(
        selected_itinerary,
        duration_days,
        daily_food_cost,
        daily_activity_cost,
        daily_transport_cost
    )
    
    return {
        "itinerary": selected_itinerary,
        "best_for_budget": best_for_budget,
        "estimated_cost": estimated_cost,
        "budget": parse_budget(budget)
    }


if __name__ == "__main__":
    # Example usage
    from app.helpers.openai_helper import HotelRecommendation, DayPlan, Activity
    
    # Create sample itineraries
    sample_itineraries = MultipleItinerariesOutput(
        itineraries=[
            ItineraryOutput(
                destination="Amritsar",
                summary="Budget-friendly cultural trip",
                hotels=[
                    HotelRecommendation(
                        name="Budget Hotel",
                        location="City Center",
                        rating=3.5,
                        price_per_night=1500,
                        distance_to_center_km=1.0,
                        reasons=["Affordable", "Good location"]
                    )
                ],
                day_plans=[
                    DayPlan(
                        day=1,
                        date="2026-01-10",
                        summary="Explore Golden Temple",
                        activities=[
                            Activity(
                                time="09:00",
                                title="Visit Golden Temple",
                                description="Morning visit",
                                poi="Golden Temple"
                            )
                        ]
                    )
                ]
            ),
            ItineraryOutput(
                destination="Amritsar",
                summary="Luxury experience",
                hotels=[
                    HotelRecommendation(
                        name="Luxury Hotel",
                        location="City Center",
                        rating=4.5,
                        price_per_night=5000,
                        distance_to_center_km=0.5,
                        reasons=["Luxury", "Premium location"]
                    )
                ],
                day_plans=[
                    DayPlan(
                        day=1,
                        date="2026-01-10",
                        summary="Luxury day",
                        activities=[
                            Activity(
                                time="09:00",
                                title="Luxury experience",
                                description="Premium activities",
                                poi=None
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    nlp_data = {
        "budget": "₹20000",
        "duration_days": 3
    }
    
    result = optimize_budget(sample_itineraries, nlp_data)
    print(f"Selected itinerary: {result['itinerary'].summary}")
    print(f"Best for budget: {result['best_for_budget']}")
    print(f"Estimated cost: ₹{result['estimated_cost']:.2f}")
    print(f"Budget: ₹{result['budget']}")
