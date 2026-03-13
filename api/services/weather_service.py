"""
Weather Service for Parks Finder

Uses Open-Meteo API (free, no API key required) to fetch current weather
and provide mom-friendly recommendations based on conditions.
"""
import time
import httpx
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class WeatherCondition(str, Enum):
    """Weather condition categories."""
    SUNNY = "sunny"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    SNOWY = "snowy"
    FOGGY = "foggy"


@dataclass
class WeatherData:
    """Current weather data."""
    temperature_f: float
    feels_like_f: float
    humidity: int
    precipitation_probability: int
    precipitation_mm: float
    weather_code: int
    condition: WeatherCondition
    uv_index: float
    wind_speed_mph: float
    is_daytime: bool

    # Mom-friendly recommendations
    mom_tip: str
    suggested_activities: list[str]
    things_to_avoid: list[str]
    suggested_queries: list[str]


# WMO Weather interpretation codes
# https://open-meteo.com/en/docs
WMO_CODES = {
    0: WeatherCondition.SUNNY,      # Clear sky
    1: WeatherCondition.SUNNY,      # Mainly clear
    2: WeatherCondition.PARTLY_CLOUDY,  # Partly cloudy
    3: WeatherCondition.CLOUDY,     # Overcast
    45: WeatherCondition.FOGGY,     # Foggy
    48: WeatherCondition.FOGGY,     # Depositing rime fog
    51: WeatherCondition.RAINY,     # Light drizzle
    53: WeatherCondition.RAINY,     # Moderate drizzle
    55: WeatherCondition.RAINY,     # Dense drizzle
    61: WeatherCondition.RAINY,     # Slight rain
    63: WeatherCondition.RAINY,     # Moderate rain
    65: WeatherCondition.RAINY,     # Heavy rain
    71: WeatherCondition.SNOWY,     # Slight snow
    73: WeatherCondition.SNOWY,     # Moderate snow
    75: WeatherCondition.SNOWY,     # Heavy snow
    80: WeatherCondition.RAINY,     # Slight rain showers
    81: WeatherCondition.RAINY,     # Moderate rain showers
    82: WeatherCondition.RAINY,     # Violent rain showers
    95: WeatherCondition.STORMY,    # Thunderstorm
    96: WeatherCondition.STORMY,    # Thunderstorm with slight hail
    99: WeatherCondition.STORMY,    # Thunderstorm with heavy hail
}


class WeatherService:
    """
    Weather service using Open-Meteo API.
    Caches results for 30 minutes to avoid excessive API calls.
    """

    # Fairfax County, VA coordinates (center of county)
    DEFAULT_LAT = 38.8462
    DEFAULT_LON = -77.3064

    # Cache duration in seconds (30 minutes)
    CACHE_DURATION = 1800

    def __init__(self):
        self._cache: Optional[WeatherData] = None
        self._cache_time: float = 0
        self._cache_lat: float = 0
        self._cache_lon: float = 0

    def _is_cache_valid(self, lat: float, lon: float) -> bool:
        """Check if cached data is still valid."""
        if self._cache is None:
            return False
        if time.time() - self._cache_time > self.CACHE_DURATION:
            return False
        # Check if coordinates are close enough (within ~1 mile)
        if abs(lat - self._cache_lat) > 0.015 or abs(lon - self._cache_lon) > 0.015:
            return False
        return True

    async def get_current_weather(
        self,
        lat: float = DEFAULT_LAT,
        lon: float = DEFAULT_LON
    ) -> WeatherData:
        """
        Get current weather for the specified location.
        Uses cached data if available and fresh.
        """
        # Return cached data if valid
        if self._is_cache_valid(lat, lon):
            return self._cache

        # Fetch fresh data from Open-Meteo
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "is_day"
            ],
            "hourly": ["uv_index", "precipitation_probability"],
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "mm",
            "timezone": "America/New_York",
            "forecast_days": 1
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        current = data["current"]
        hourly = data["hourly"]

        # Get current hour index for hourly data
        current_hour = 12  # Default to noon
        try:
            from datetime import datetime
            now = datetime.now()
            current_hour = now.hour
        except Exception:
            pass

        # Extract values
        temp_f = current["temperature_2m"]
        feels_like_f = current["apparent_temperature"]
        humidity = current["relative_humidity_2m"]
        precipitation_mm = current["precipitation"]
        weather_code = current["weather_code"]
        wind_speed = current["wind_speed_10m"]
        is_daytime = current["is_day"] == 1

        # Get UV and precipitation probability from hourly
        uv_index = hourly["uv_index"][current_hour] if current_hour < len(hourly["uv_index"]) else 5
        precip_prob = hourly["precipitation_probability"][current_hour] if current_hour < len(hourly["precipitation_probability"]) else 0

        # Determine condition
        condition = WMO_CODES.get(weather_code, WeatherCondition.CLOUDY)

        # Generate mom-friendly recommendations
        mom_tip, activities, avoid, queries = self._generate_recommendations(
            temp_f, feels_like_f, condition, uv_index, precip_prob, humidity
        )

        weather_data = WeatherData(
            temperature_f=temp_f,
            feels_like_f=feels_like_f,
            humidity=humidity,
            precipitation_probability=precip_prob,
            precipitation_mm=precipitation_mm,
            weather_code=weather_code,
            condition=condition,
            uv_index=uv_index,
            wind_speed_mph=wind_speed,
            is_daytime=is_daytime,
            mom_tip=mom_tip,
            suggested_activities=activities,
            things_to_avoid=avoid,
            suggested_queries=queries
        )

        # Update cache
        self._cache = weather_data
        self._cache_time = time.time()
        self._cache_lat = lat
        self._cache_lon = lon

        return weather_data

    def _generate_recommendations(
        self,
        temp_f: float,
        feels_like_f: float,
        condition: WeatherCondition,
        uv_index: float,
        precip_prob: int,
        humidity: int
    ) -> tuple[str, list[str], list[str], list[str]]:
        """Generate mom-friendly recommendations based on weather."""

        activities = []
        avoid = []
        queries = []
        mom_tip = ""

        # Temperature-based recommendations
        if feels_like_f >= 90:
            mom_tip = "It's hot! Look for splash pads and shaded playgrounds."
            activities.extend(["splash pads", "shaded playgrounds", "parks with pavilions"])
            avoid.extend(["unshaded playgrounds", "long hikes", "metal slides"])
            queries.extend([
                "Find a splash pad near me",
                "Parks with good shade",
                "Where can we cool off today?"
            ])
        elif feels_like_f >= 85:
            mom_tip = "Warm day - bring water and sunscreen!"
            activities.extend(["splash pads", "shaded areas", "morning visits"])
            avoid.extend(["midday playground visits"])
            queries.extend([
                "Shaded playgrounds nearby",
                "Parks with water features"
            ])
        elif feels_like_f >= 65:
            mom_tip = "Perfect playground weather!"
            activities.extend(["playgrounds", "trails", "picnics", "nature walks"])
            queries.extend([
                "Best playgrounds nearby",
                "Good trails for kids",
                "Parks good for picnics"
            ])
        elif feels_like_f >= 50:
            mom_tip = "Nice but bring a jacket for the little ones."
            activities.extend(["playgrounds", "short walks", "nature centers"])
            avoid.extend(["water play"])
            queries.extend([
                "Playgrounds with restrooms nearby",
                "Nature centers near me"
            ])
        elif feels_like_f >= 32:
            mom_tip = "Bundle up! Keep visits short."
            activities.extend(["quick playground visits", "indoor options"])
            avoid.extend(["long outdoor activities", "water play"])
            queries.extend([
                "Indoor play areas",
                "Parks with warming shelters"
            ])
        else:
            mom_tip = "Very cold! Consider indoor activities."
            activities.extend(["indoor play areas", "nature centers"])
            avoid.extend(["outdoor playgrounds"])
            queries.extend([
                "Indoor activities for kids",
                "Nature centers near me"
            ])

        # Weather condition adjustments
        if condition in [WeatherCondition.RAINY, WeatherCondition.STORMY]:
            mom_tip = "Rainy day - look for covered areas or indoor options!"
            activities = ["covered pavilions", "indoor play", "nature centers"]
            avoid = ["open playgrounds", "trails"]
            queries = [
                "Parks with covered pavilions",
                "Indoor play areas near me",
                "What can we do on a rainy day?"
            ]
        elif condition == WeatherCondition.SNOWY:
            mom_tip = "Snow day! Bundle up for winter fun."
            activities = ["sledding hills", "winter walks", "indoor warmup spots"]
            avoid = ["regular playgrounds"]
            queries = [
                "Good sledding spots",
                "Winter activities for kids"
            ]

        # UV adjustments
        if uv_index >= 8 and condition == WeatherCondition.SUNNY:
            mom_tip += " UV is very high - seek shade and use sunscreen!"
            if "shaded playgrounds" not in activities:
                activities.insert(0, "shaded playgrounds")
            if "Shaded playgrounds nearby" not in queries:
                queries.insert(0, "Parks with good tree shade")
        elif uv_index >= 6 and condition == WeatherCondition.SUNNY:
            if "sunscreen" not in mom_tip.lower():
                mom_tip += " Don't forget sunscreen!"

        # High humidity adjustments
        if humidity >= 80 and feels_like_f >= 75:
            mom_tip = "Hot and humid - stay hydrated and take breaks!"
            if "splash pads" not in activities:
                activities.insert(0, "splash pads")

        return mom_tip, activities, avoid, queries

    def get_weather_context_for_rag(self, weather: WeatherData) -> str:
        """
        Generate a weather context string to inject into RAG prompts.
        """
        context_parts = [
            f"Current weather: {weather.temperature_f:.0f}°F (feels like {weather.feels_like_f:.0f}°F), {weather.condition.value.replace('_', ' ')}"
        ]

        if weather.uv_index >= 6:
            context_parts.append(f"UV index is {weather.uv_index:.0f} (high)")

        if weather.precipitation_probability >= 50:
            context_parts.append(f"{weather.precipitation_probability}% chance of rain")

        context_parts.append(f"\nMom tip: {weather.mom_tip}")

        if weather.suggested_activities:
            context_parts.append(f"Consider recommending: {', '.join(weather.suggested_activities[:3])}")

        if weather.things_to_avoid:
            context_parts.append(f"Consider avoiding: {', '.join(weather.things_to_avoid[:2])}")

        return "\n".join(context_parts)


# Singleton instance
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Get or create the weather service singleton."""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
