#!/usr/bin/env python3
"""
Geocode all Fairfax County parks and add lat/lng coordinates to the JSON data.
Uses Apple's CLGeocoder via a free geocoding API as fallback.
"""
import json
import time
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "source_data", "fairfax_parks.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "source_data", "fairfax_parks_geocoded.json")

# Initialize geocoder with a user agent
geolocator = Nominatim(user_agent="parks_finder_geocoder")

def geocode_address(address: str, city: str, retries: int = 3) -> tuple:
    """Geocode an address, returning (lat, lng) or (None, None)."""
    if not address or address == "N/A":
        return None, None

    # Build full address
    full_address = f"{address}, {city}, Fairfax County, Virginia, USA"

    for attempt in range(retries):
        try:
            location = geolocator.geocode(full_address, timeout=10)
            if location:
                return location.latitude, location.longitude

            # Try with just city if full address fails
            fallback = f"{city}, Fairfax County, Virginia, USA"
            location = geolocator.geocode(fallback, timeout=10)
            if location:
                return location.latitude, location.longitude

            return None, None

        except GeocoderTimedOut:
            print(f"  Timeout, retrying... ({attempt + 1}/{retries})")
            time.sleep(2)
        except GeocoderServiceError as e:
            print(f"  Service error: {e}")
            time.sleep(5)

    return None, None


def main():
    print("Loading parks data...")
    with open(DATA_PATH, 'r') as f:
        parks = json.load(f)

    print(f"Found {len(parks)} parks to geocode")

    geocoded_count = 0
    failed_count = 0

    for i, park in enumerate(parks):
        park_name = park["park_name"]
        address = park.get("address", "N/A")
        city = park.get("city", "Fairfax")

        # Skip if already has coordinates
        if park.get("latitude") and park.get("longitude"):
            print(f"[{i+1}/{len(parks)}] {park_name}: Already geocoded")
            continue

        print(f"[{i+1}/{len(parks)}] Geocoding: {park_name}...", end=" ")

        lat, lng = geocode_address(address, city)

        if lat and lng:
            park["latitude"] = lat
            park["longitude"] = lng
            geocoded_count += 1
            print(f"OK ({lat:.4f}, {lng:.4f})")
        else:
            # Try geocoding by park name
            park_query = f"{park_name}, Fairfax County, Virginia"
            try:
                location = geolocator.geocode(park_query, timeout=10)
                if location:
                    park["latitude"] = location.latitude
                    park["longitude"] = location.longitude
                    geocoded_count += 1
                    print(f"OK by name ({location.latitude:.4f}, {location.longitude:.4f})")
                else:
                    failed_count += 1
                    print("FAILED")
            except Exception as e:
                failed_count += 1
                print(f"FAILED ({e})")

        # Rate limiting - Nominatim requires 1 second between requests
        time.sleep(1.1)

        # Save progress every 50 parks
        if (i + 1) % 50 == 0:
            print(f"\nSaving progress ({i+1} parks processed)...")
            with open(OUTPUT_PATH, 'w') as f:
                json.dump(parks, f, indent=2)

    # Final save
    print(f"\nSaving final output to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(parks, f, indent=2)

    print(f"\nDone!")
    print(f"  Geocoded: {geocoded_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(parks)}")


if __name__ == "__main__":
    main()
