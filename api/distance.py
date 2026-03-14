"""
Distance and Drive Time Calculations

Uses Haversine formula for straight-line distance,
then estimates drive time based on typical Fairfax County speeds.

Distance Categories:
- "Near" = within 10 min drive
- "Moderately close" = 10-15 min drive
- "Driveable" = 15+ min drive
"""
import math
from typing import Dict, Any

# Average driving speed in Fairfax County (mph)
# Accounts for traffic lights, suburban roads
AVG_SPEED_MPH = 25  # Conservative estimate for suburban driving

# Distance category thresholds (in minutes)
DISTANCE_CATEGORIES = {
    "near": {
        "max_minutes": 10,
        "label": "Near you",
        "emoji": "📍"
    },
    "moderate": {
        "min_minutes": 10,
        "max_minutes": 15,
        "label": "Moderately close",
        "emoji": "🚗"
    },
    "driveable": {
        "min_minutes": 15,
        "label": "Driveable",
        "emoji": "🛣️"
    }
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate straight-line distance between two points using Haversine formula.

    Returns distance in miles.
    """
    # Earth's radius in miles
    R = 3959

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def estimate_drive_time(distance_miles: float, speed_mph: float = AVG_SPEED_MPH) -> float:
    """
    Estimate drive time in minutes.

    Adds a 1.3x factor to account for non-straight routes in suburban areas.
    """
    # Suburban roads aren't straight - multiply by route factor
    route_factor = 1.3
    actual_distance = distance_miles * route_factor

    # Time = Distance / Speed (convert to minutes)
    time_hours = actual_distance / speed_mph
    return time_hours * 60


def categorize_distance(drive_time_minutes: float) -> Dict[str, Any]:
    """
    Categorize drive time into user-friendly labels.

    Returns:
        {
            "category": "near" | "moderate" | "driveable",
            "label": "Near you",
            "emoji": "📍",
            "minutes": 8
        }
    """
    if drive_time_minutes <= DISTANCE_CATEGORIES["near"]["max_minutes"]:
        return {
            "category": "near",
            **DISTANCE_CATEGORIES["near"],
            "minutes": round(drive_time_minutes)
        }
    elif drive_time_minutes <= DISTANCE_CATEGORIES["moderate"]["max_minutes"]:
        return {
            "category": "moderate",
            **DISTANCE_CATEGORIES["moderate"],
            "minutes": round(drive_time_minutes)
        }
    else:
        return {
            "category": "driveable",
            **DISTANCE_CATEGORIES["driveable"],
            "minutes": round(drive_time_minutes)
        }


def get_distance_info(
    user_lat: float,
    user_lng: float,
    park_lat: float,
    park_lng: float
) -> Dict[str, Any]:
    """
    Get complete distance information for a park.

    Returns:
        {
            "distance_miles": 5.2,
            "drive_time_minutes": 12,
            "category": "moderate",
            "label": "Moderately close",
            "emoji": "🚗",
            "display": "12 min drive"
        }
    """
    distance = haversine_distance(user_lat, user_lng, park_lat, park_lng)
    drive_time = estimate_drive_time(distance)
    category_info = categorize_distance(drive_time)

    return {
        "distance_miles": round(distance, 1),
        "drive_time_minutes": round(drive_time),
        **category_info,
        "display": f"{round(drive_time)} min drive"
    }


def format_distance_for_prompt(distance_info: Dict[str, Any]) -> str:
    """
    Format distance info for inclusion in RAG prompts.

    Example: "Near you (8 min drive)" or "Driveable (22 min drive)"
    """
    return f"{distance_info['label']} ({distance_info['display']})"


# ============================================================
# SAMPLE FAIRFAX COUNTY LOCATIONS (for testing)
# ============================================================

SAMPLE_LOCATIONS = {
    # User home locations
    "fairfax_city": (38.8462, -77.3064),
    "reston": (38.9586, -77.3570),
    "mclean": (38.9339, -77.1773),
    "springfield": (38.7893, -77.1872),
    "herndon": (38.9696, -77.3861),

    # Park locations (approximate)
    "burke_lake_park": (38.7608, -77.2997),
    "clemyjontri_park": (38.9547, -77.1847),
    "great_falls_park": (38.9985, -77.2519),
    "lake_fairfax_park": (38.9647, -77.3386),
    "huntley_meadows": (38.7561, -77.1019),
}


if __name__ == "__main__":
    # Test distance calculations
    print("Distance Test: Fairfax City to various parks\n")

    user_loc = SAMPLE_LOCATIONS["fairfax_city"]

    for park_name, park_loc in SAMPLE_LOCATIONS.items():
        if "park" in park_name:
            info = get_distance_info(user_loc[0], user_loc[1], park_loc[0], park_loc[1])
            print(f"{park_name}:")
            print(f"  {info['distance_miles']} miles")
            print(f"  {format_distance_for_prompt(info)}")
            print()
