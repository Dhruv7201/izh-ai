import sys
import requests
from typing import Dict, List, Optional, Any
from app.config.settings import settings

# API Configuration
API_KEY = settings.OPEN_WEATHER_MAP_API_KEY
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_weather_data(location: str) -> Dict[str, Any]:
    """
    Fetch weather data for a given location.
    
    Args:
        location: City name or location string
        
    Returns:
        Dictionary containing raw weather data from API
        
    Raises:
        requests.exceptions.RequestException: If API request fails
        KeyError: If response format is unexpected
    """
    params = {
        "q": location,
        "appid": API_KEY,
        "units": "metric"
    }
    
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def categorize_weather(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Categorize weather based on temperature, wind, humidity, and other parameters.
    Returns structured categories useful for GPT-4o itinerary generation.
    
    Args:
        weather_data: Raw weather data from OpenWeatherMap API
        
    Returns:
        Dictionary with categorized weather information
    """
    # Extract key parameters
    main = weather_data.get("main", {})
    weather = weather_data.get("weather", [{}])[0]
    wind = weather_data.get("wind", {})
    clouds = weather_data.get("clouds", {})
    visibility = weather_data.get("visibility", 10000)
    
    temp = main.get("temp", 20)
    feels_like = main.get("feels_like", temp)
    humidity = main.get("humidity", 50)
    pressure = main.get("pressure", 1013)
    temp_min = main.get("temp_min", temp)
    temp_max = main.get("temp_max", temp)
    
    wind_speed = wind.get("speed", 0)
    wind_gust = wind.get("gust", 0)
    cloudiness = clouds.get("all", 0)
        
    weather_main = weather.get("main", "").lower()
    weather_description = weather.get("description", "").lower()
    weather_id = weather.get("id", 800)
    
    # Temperature categories
    temp_category = _categorize_temperature(temp, feels_like)
    
    # Precipitation categories
    precipitation_category = _categorize_precipitation(weather_main, weather_description, weather_id)
    
    # Wind categories
    wind_category = _categorize_wind(wind_speed, wind_gust)
    
    # Visibility/Fog categories
    visibility_category = _categorize_visibility(visibility, weather_description, humidity)
    
    # Cloud cover categories
    cloud_category = _categorize_clouds(cloudiness, weather_main)
    
    # Overall weather condition
    overall_condition = _determine_overall_condition(
        weather_main, weather_description, temp_category, precipitation_category
    )
    
    # Comfort level (for itinerary planning)
    comfort_level = _assess_comfort_level(feels_like, humidity, wind_speed, weather_main)
    
    return {
        "categories": {
            "temperature": temp_category,
            "precipitation": precipitation_category,
            "wind": wind_category,
            "visibility": visibility_category,
            "cloud_cover": cloud_category,
            "overall_condition": overall_condition,
            "comfort_level": comfort_level
        },
        "raw_metrics": {
            "temperature_celsius": round(temp, 1),
            "feels_like_celsius": round(feels_like, 1),
            "temp_min_celsius": round(temp_min, 1),
            "temp_max_celsius": round(temp_max, 1),
            "humidity_percent": humidity,
            "pressure_hpa": pressure,
            "wind_speed_ms": round(wind_speed, 1),
            "wind_gust_ms": round(wind_gust, 1) if wind_gust else None,
            "cloudiness_percent": cloudiness,
            "visibility_meters": visibility if visibility else None,
            "weather_main": weather_main,
            "weather_description": weather_description
        },
        "itinerary_recommendations": _generate_itinerary_recommendations(
            temp_category, precipitation_category, wind_category, 
            visibility_category, overall_condition, comfort_level
        )
    }


def _categorize_temperature(temp: float, feels_like: float) -> Dict[str, Any]:
    """Categorize temperature into cold, cool, mild, warm, hot."""
    # Use feels_like for categorization as it's more accurate for human perception
    temp_to_use = feels_like
    
    if temp_to_use < 0:
        category = "freezing"
        intensity = "extreme"
    elif temp_to_use < 5:
        category = "very_cold"
        intensity = "high"
    elif temp_to_use < 10:
        category = "cold"
        intensity = "moderate"
    elif temp_to_use < 15:
        category = "cool"
        intensity = "mild"
    elif temp_to_use < 22:
        category = "mild"
        intensity = "comfortable"
    elif temp_to_use < 28:
        category = "warm"
        intensity = "comfortable"
    elif temp_to_use < 35:
        category = "hot"
        intensity = "moderate"
    elif temp_to_use < 40:
        category = "very_hot"
        intensity = "high"
    else:
        category = "extremely_hot"
        intensity = "extreme"
    
    return {
        "category": category,
        "intensity": intensity,
        "actual_temp": round(temp, 1),
        "feels_like": round(feels_like, 1)
    }


def _categorize_precipitation(weather_main: str, description: str, weather_id: int) -> Dict[str, Any]:
    """Categorize precipitation: dry, light_rain, moderate_rain, heavy_rain, snow, etc."""
    # Weather ID ranges from OpenWeatherMap
    # 2xx = Thunderstorm, 3xx = Drizzle, 5xx = Rain, 6xx = Snow, 7xx = Atmosphere (fog, etc.)
    
    if weather_id >= 200 and weather_id < 300:
        return {"type": "stormy", "intensity": "thunderstorm", "has_precipitation": True}
    elif weather_id >= 300 and weather_id < 400:
        return {"type": "rainy", "intensity": "light_drizzle", "has_precipitation": True}
    elif weather_id >= 500 and weather_id < 600:
        if weather_id < 502:
            intensity = "light_rain"
        elif weather_id < 504:
            intensity = "moderate_rain"
        elif weather_id < 511:
            intensity = "heavy_rain"
        else:
            intensity = "freezing_rain"
        return {"type": "rainy", "intensity": intensity, "has_precipitation": True}
    elif weather_id >= 600 and weather_id < 700:
        if weather_id < 602:
            intensity = "light_snow"
        elif weather_id < 622:
            intensity = "moderate_snow"
        else:
            intensity = "heavy_snow"
        return {"type": "snowy", "intensity": intensity, "has_precipitation": True}
    elif weather_id >= 700 and weather_id < 800:
        return {"type": "atmospheric", "intensity": weather_main, "has_precipitation": False}
    else:
        return {"type": "dry", "intensity": "none", "has_precipitation": False}


def _categorize_wind(wind_speed: float, wind_gust: float) -> Dict[str, Any]:
    """Categorize wind: calm, breezy, windy, very_windy."""
    # Wind speed in m/s
    max_wind = max(wind_speed, wind_gust) if wind_gust else wind_speed
    
    if max_wind < 2:
        category = "calm"
        intensity = "very_low"
    elif max_wind < 5:
        category = "light_breeze"
        intensity = "low"
    elif max_wind < 10:
        category = "breezy"
        intensity = "moderate"
    elif max_wind < 15:
        category = "windy"
        intensity = "moderate_high"
    elif max_wind < 20:
        category = "very_windy"
        intensity = "high"
    else:
        category = "extremely_windy"
        intensity = "extreme"
    
    return {
        "category": category,
        "intensity": intensity,
        "speed_ms": round(wind_speed, 1),
        "gust_ms": round(wind_gust, 1) if wind_gust else None
    }


def _categorize_visibility(visibility: int, description: str, humidity: float) -> Dict[str, Any]:
    """Categorize visibility: clear, hazy, foggy."""
    # Visibility in meters, typically 0-10000
    # Fog conditions
    if "fog" in description or "mist" in description:
        if visibility < 1000:
            return {"category": "dense_fog", "intensity": "extreme", "visibility_meters": visibility}
        elif visibility < 5000:
            return {"category": "foggy", "intensity": "moderate", "visibility_meters": visibility}
        else:
            return {"category": "hazy", "intensity": "light", "visibility_meters": visibility}
    
    # High humidity can cause haze
    if humidity > 80 and visibility < 5000:
        return {"category": "hazy", "intensity": "moderate", "visibility_meters": visibility}
    
    if visibility >= 10000:
        return {"category": "clear", "intensity": "excellent", "visibility_meters": visibility}
    elif visibility >= 5000:
        return {"category": "clear", "intensity": "good", "visibility_meters": visibility}
    elif visibility >= 1000:
        return {"category": "hazy", "intensity": "light", "visibility_meters": visibility}
    else:
        return {"category": "poor", "intensity": "moderate", "visibility_meters": visibility}


def _categorize_clouds(cloudiness: float, weather_main: str) -> Dict[str, Any]:
    """Categorize cloud cover: clear, partly_cloudy, cloudy, overcast."""
    if cloudiness < 10:
        return {"category": "clear", "intensity": "none", "cloudiness_percent": cloudiness}
    elif cloudiness < 25:
        return {"category": "mostly_clear", "intensity": "very_low", "cloudiness_percent": cloudiness}
    elif cloudiness < 50:
        return {"category": "partly_cloudy", "intensity": "low", "cloudiness_percent": cloudiness}
    elif cloudiness < 75:
        return {"category": "cloudy", "intensity": "moderate", "cloudiness_percent": cloudiness}
    else:
        return {"category": "overcast", "intensity": "high", "cloudiness_percent": cloudiness}


def _determine_overall_condition(
    weather_main: str, description: str, temp_category: Dict, precipitation_category: Dict
) -> str:
    """Determine overall weather condition for quick reference."""
    precip_type = precipitation_category.get("type", "dry")
    
    if precip_type == "stormy":
        return "stormy"
    elif precip_type == "rainy":
        return "rainy"
    elif precip_type == "snowy":
        return "snowy"
    elif "fog" in description or "mist" in description:
        return "foggy"
    elif temp_category["category"] in ["freezing", "very_cold", "cold"]:
        return "cold"
    elif temp_category["category"] in ["very_hot", "extremely_hot", "hot"]:
        return "hot"
    elif weather_main == "clear":
        return "clear"
    elif weather_main == "clouds":
        return "cloudy"
    else:
        return "moderate"


def _assess_comfort_level(
    feels_like: float, humidity: float, wind_speed: float, weather_main: str
) -> Dict[str, Any]:
    """Assess overall comfort level for outdoor activities."""
    # Temperature comfort
    if 18 <= feels_like <= 26:
        temp_comfort = "comfortable"
    elif 15 <= feels_like < 18 or 26 < feels_like <= 30:
        temp_comfort = "moderate"
    else:
        temp_comfort = "uncomfortable"
    
    # Humidity comfort (high humidity makes it feel worse)
    if humidity > 80:
        humidity_comfort = "uncomfortable"
    elif humidity > 60:
        humidity_comfort = "moderate"
    else:
        humidity_comfort = "comfortable"
    
    # Wind comfort (moderate wind can be cooling, too much is uncomfortable)
    if 2 <= wind_speed <= 10:
        wind_comfort = "comfortable"  # Cooling breeze
    elif wind_speed < 2:
        wind_comfort = "moderate"  # Might feel stuffy
    else:
        wind_comfort = "uncomfortable"  # Too windy
    
    # Overall comfort
    if temp_comfort == "comfortable" and humidity_comfort == "comfortable" and wind_comfort in ["comfortable", "moderate"]:
        overall = "very_comfortable"
    elif temp_comfort == "uncomfortable" or humidity_comfort == "uncomfortable" or wind_comfort == "uncomfortable":
        overall = "uncomfortable"
    else:
        overall = "moderately_comfortable"
    
    return {
        "overall": overall,
        "temperature_comfort": temp_comfort,
        "humidity_comfort": humidity_comfort,
        "wind_comfort": wind_comfort
    }


def _generate_itinerary_recommendations(
    temp_category: Dict, precipitation_category: Dict, wind_category: Dict,
    visibility_category: Dict, overall_condition: str, comfort_level: Dict
) -> List[str]:
    """Generate human-readable recommendations for itinerary planning."""
    recommendations = []
    
    # Temperature-based recommendations
    temp_cat = temp_category.get("category", "mild")
    if temp_cat in ["freezing", "very_cold", "cold"]:
        recommendations.append("Dress warmly with layers; consider indoor activities")
    elif temp_cat in ["hot", "very_hot", "extremely_hot"]:
        recommendations.append("Stay hydrated; seek shade or air-conditioned spaces; plan activities during cooler hours")
    elif temp_cat in ["warm", "mild"]:
        recommendations.append("Pleasant weather for outdoor activities")
    
    # Precipitation-based recommendations
    if precipitation_category.get("has_precipitation", False):
        precip_type = precipitation_category.get("type", "rainy")
        if precip_type == "rainy":
            recommendations.append("Carry an umbrella or raincoat; consider indoor alternatives")
        elif precip_type == "snowy":
            recommendations.append("Dress for snow; be cautious on roads and paths")
        elif precip_type == "stormy":
            recommendations.append("Avoid outdoor activities; seek shelter if outdoors")
    else:
        recommendations.append("No precipitation expected; good for outdoor plans")
    
    # Wind-based recommendations
    wind_intensity = wind_category.get("intensity", "low")
    if wind_intensity in ["high", "extreme"]:
        recommendations.append("Strong winds expected; secure loose items; be cautious near water")
    elif wind_intensity == "moderate":
        recommendations.append("Moderate breeze; pleasant for most activities")
    
    # Visibility-based recommendations
    if visibility_category.get("category") == "foggy":
        recommendations.append("Reduced visibility; drive carefully; consider postponing scenic activities")
    
    # Comfort-based recommendations
    if comfort_level.get("overall") == "very_comfortable":
        recommendations.append("Excellent weather conditions for outdoor activities")
    elif comfort_level.get("overall") == "uncomfortable":
        recommendations.append("Weather conditions may be uncomfortable; plan accordingly")
    
    return recommendations


def get_weather_categories(location: str) -> Dict[str, Any]:
    """
    Main function to fetch and categorize weather for a location.
    This is the primary function to use for itinerary generation.
    
    Args:
        location: City name or location string
        
    Returns:
        Dictionary with categorized weather information suitable for GPT-4o
        
    Example:
        >>> weather_info = get_weather_categories("Paris")
        >>> print(weather_info["categories"]["overall_condition"])
        "rainy"
    """
    try:
        weather_data = fetch_weather_data(location)
        categorized = categorize_weather(weather_data)
        return categorized
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"Failed to fetch weather data: {e}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Weather API request failed: {e}")
    except KeyError as e:
        raise ValueError(f"Unexpected weather API response format: {e}")


# CLI support for backward compatibility
if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "moscow"
    
    try:
        result = get_weather_categories(city)
        
        # Print formatted output
        print(f"\n📊 Weather Categories:")
        print(f"  • Overall Condition: {result['categories']['overall_condition']}")
        print(f"  • Temperature: {result['categories']['temperature']['category']} ({result['raw_metrics']['temperature_celsius']}°C, feels like {result['raw_metrics']['feels_like_celsius']}°C)")
        print(f"  • Precipitation: {result['categories']['precipitation']['type']} ({result['categories']['precipitation']['intensity']})")
        print(f"  • Wind: {result['categories']['wind']['category']} ({result['categories']['wind']['intensity']})")
        print(f"  • Visibility: {result['categories']['visibility']['category']}")
        print(f"  • Cloud Cover: {result['categories']['cloud_cover']['category']}")
        print(f"  • Comfort Level: {result['categories']['comfort_level']['overall']}")
        
        print(f"\n💡 Itinerary Recommendations:")
        for rec in result['itinerary_recommendations']:
            print(f"  • {rec}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
