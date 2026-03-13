"""
Fetch all parks from Fairfax County ArcGIS API and aggregate duplicate entries.
Parks like Burke Lake have multiple API entries (Marina, Golf, Campground)
that should be merged into a single comprehensive entry.

API: https://www.fairfaxcounty.gov/gispub2/rest/services/FCPA/ParkAmenityLocator/FeatureServer/0
"""
import json
import requests
from collections import defaultdict

# Fairfax County Park Authority ArcGIS REST API
API_URL = "https://www.fairfaxcounty.gov/gispub2/rest/services/FCPA/ParkAmenityLocator/FeatureServer/0/query"
OUTPUT_FILE = "source_data/fairfax_parks.json"

def fetch_all_parks():
    """Fetch all parks from the ArcGIS API."""
    print("Fetching parks from Fairfax County ArcGIS API...")

    params = {
        "where": "1=1",  # Get all records
        "outFields": "*",  # All fields
        "f": "json",  # JSON format
        "resultRecordCount": 2000  # Max records
    }

    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    features = data.get("features", [])
    # Extract attributes from each feature
    records = [f.get("attributes", {}) for f in features]

    print(f"Fetched {len(records)} records from API")
    return records

def aggregate_parks(raw_data):
    """
    Aggregate multiple API entries for the same park into one entry.
    Combines amenities from all sections (Marina, Golf, Campground, etc.)
    """
    parks_dict = defaultdict(lambda: {
        "park_name": "",
        "classification": "",
        "address": "",
        "city": "",
        "description": "",
        "sections": [],
        "website": "",
        "phone": "",
        "amenities": {
            "playground": "No",
            "restrooms": "No",
            "picnic_shelters": "No",
            "trails": "None",
            "parking": "Unknown",
            "water_activities": "None",
            "special_features": [],
            "dog_friendly": "Unknown"
        },
        "best_for": []
    })

    for record in raw_data:
        park_name = (record.get("PARK_NAME") or "").strip()
        if not park_name:
            continue

        park = parks_dict[park_name]

        # Set basic info (use first encountered or update if empty)
        if not park["park_name"]:
            park["park_name"] = park_name
        if not park["classification"] and record.get("PARK_CLASSIFICATION"):
            park["classification"] = record.get("PARK_CLASSIFICATION", "")
        if not park["address"] and record.get("ADDRESS"):
            park["address"] = record.get("ADDRESS", "")
        if not park["city"] and record.get("CITY"):
            park["city"] = record.get("CITY", "")
        if not park["website"] and record.get("WEBSITE_LINK"):
            park["website"] = record.get("WEBSITE_LINK", "")
        if not park["phone"] and record.get("CONTACT_PHONE"):
            park["phone"] = record.get("CONTACT_PHONE", "")

        # Track section names
        section_name = record.get("PARK_SECTION_NAME") or record.get("LOCATION_NAME") or ""
        if section_name and section_name not in park["sections"]:
            park["sections"].append(section_name)

        # Aggregate amenities
        amenities = park["amenities"]

        # Playground
        playground = record.get("PLAYGROUNDS_AND_PLAY_FEATURES")
        if playground and playground not in ["None", "No", ""]:
            if amenities["playground"] == "No":
                amenities["playground"] = playground
            elif playground not in amenities["playground"]:
                amenities["playground"] += f"; {playground}"

        # Restrooms
        if record.get("RESTROOMS") and record.get("RESTROOMS") not in ["None", "No", ""]:
            amenities["restrooms"] = "Yes"

        # Picnic
        if record.get("PICNIC_SHELTERS") and record.get("PICNIC_SHELTERS") not in ["None", "No", ""]:
            amenities["picnic_shelters"] = record.get("PICNIC_SHELTERS")
        elif record.get("PICNIC_AREA") and record.get("PICNIC_AREA") not in ["None", "No", ""]:
            amenities["picnic_shelters"] = "Yes"

        # Trails
        trails = record.get("TRAILS")
        trail_features = record.get("TRAIL_FEATURES")
        if trails and trails not in ["None", "No", ""]:
            if amenities["trails"] == "None":
                amenities["trails"] = trails
                if trail_features:
                    amenities["trails"] += f" ({trail_features})"
            elif trails not in amenities["trails"]:
                amenities["trails"] += f", {trails}"

        # Parking
        parking = record.get("PARKING")
        if parking and parking not in ["None", "No", ""]:
            amenities["parking"] = parking

        # Water activities
        water = []
        if record.get("FISHING") and record.get("FISHING") not in ["None", "No", ""]:
            water.append(f"Fishing: {record.get('FISHING')}")
        if record.get("BOATING") and record.get("BOATING") not in ["None", "No", ""]:
            water.append(f"Boating: {record.get('BOATING')}")
        if record.get("SWIMMING") and record.get("SWIMMING") not in ["None", "No", ""]:
            water.append(f"Swimming: {record.get('SWIMMING')}")
        if record.get("WATER_PLAY") and record.get("WATER_PLAY") not in ["None", "No", ""]:
            water.append(f"Water play: {record.get('WATER_PLAY')}")
        if record.get("WATER_FEATURE") and record.get("WATER_FEATURE") not in ["None", "No", ""]:
            water.append(record.get("WATER_FEATURE"))

        if water:
            if amenities["water_activities"] == "None":
                amenities["water_activities"] = ", ".join(water)
            else:
                for w in water:
                    if w not in amenities["water_activities"]:
                        amenities["water_activities"] += f", {w}"

        # Dog park
        dog_park = record.get("DOG_PARK")
        if dog_park and dog_park not in ["None", "No", ""]:
            amenities["dog_friendly"] = f"Yes - {dog_park}"

        # Special features
        special_fields = {
            "CAROUSEL": "Carousel",
            "AMPHITHEATER": "Amphitheater",
            "HISTORIC_FEATURE": None,  # Use value directly
            "VISITOR_CENTER": "Visitor center",
            "CAMPGROUNDS": None,
            "GARDEN_PLOTS": "Garden plots",
            "DISC_GOLF": "Disc golf",
            "SKATEPARK": "Skate park",
        }

        for field, label in special_fields.items():
            value = record.get(field)
            if value and value not in ["None", "No", ""]:
                feature_name = label if label else value
                if feature_name not in amenities["special_features"]:
                    amenities["special_features"].append(feature_name)

        # Sports courts
        sports = []
        if record.get("TENNIS_COURTS") and record.get("TENNIS_COURTS") not in ["None", "No", ""]:
            sports.append(f"Tennis: {record.get('TENNIS_COURTS')}")
        if record.get("PICKLEBALL_COURTS") and record.get("PICKLEBALL_COURTS") not in ["None", "No", ""]:
            sports.append(f"Pickleball: {record.get('PICKLEBALL_COURTS')}")
        if record.get("BASKETBALL_COURTS") and record.get("BASKETBALL_COURTS") not in ["None", "No", ""]:
            sports.append(f"Basketball: {record.get('BASKETBALL_COURTS')}")
        if record.get("VOLLEYBALL_COURTS") and record.get("VOLLEYBALL_COURTS") not in ["None", "No", ""]:
            sports.append(f"Volleyball: {record.get('VOLLEYBALL_COURTS')}")
        if record.get("DIAMOND_FIELDS") and record.get("DIAMOND_FIELDS") not in ["None", "No", ""]:
            sports.append(f"Baseball/Softball: {record.get('DIAMOND_FIELDS')}")
        if record.get("RECTANGLE_FIELDS") and record.get("RECTANGLE_FIELDS") not in ["None", "No", ""]:
            sports.append(f"Soccer/Football: {record.get('RECTANGLE_FIELDS')}")

        for sport in sports:
            if sport not in amenities["special_features"]:
                amenities["special_features"].append(sport)

        # Golf
        if record.get("GOLF_NUMBER_OF_HOLES") and record.get("GOLF_NUMBER_OF_HOLES") not in ["None", "No", ""]:
            golf_info = f"Golf: {record.get('GOLF_NUMBER_OF_HOLES')}"
            if record.get("GOLF_PAR"):
                golf_info += f", Par {record.get('GOLF_PAR')}"
            if golf_info not in amenities["special_features"]:
                amenities["special_features"].append(golf_info)

    # Convert to list and generate descriptions
    parks_list = []
    for park_name, park_data in parks_dict.items():
        # Generate description from sections
        if park_data["sections"]:
            sections_str = ", ".join(park_data["sections"][:5])
            if len(park_data["sections"]) > 5:
                sections_str += f" and {len(park_data['sections']) - 5} more areas"
            park_data["description"] = f"Features: {sections_str}"
        else:
            park_data["description"] = f"A {park_data['classification']} park in Fairfax County."

        # Generate best_for based on amenities
        best_for = []
        if park_data["amenities"]["playground"] != "No":
            best_for.append("Families with children")
        if "Fishing" in park_data["amenities"]["water_activities"]:
            best_for.append("Fishing")
        if park_data["amenities"]["trails"] != "None":
            best_for.append("Hiking/Walking")
        if "Yes" in park_data["amenities"]["dog_friendly"]:
            best_for.append("Dog owners")
        if park_data["amenities"]["picnic_shelters"] not in ["No", "None"]:
            best_for.append("Picnics")
        if any("Tennis" in f or "Basketball" in f or "Soccer" in f for f in park_data["amenities"]["special_features"]):
            best_for.append("Sports")
        if any("Golf" in f for f in park_data["amenities"]["special_features"]):
            best_for.append("Golfers")

        park_data["best_for"] = best_for if best_for else ["General recreation"]

        # Remove sections from final output
        del park_data["sections"]

        parks_list.append(park_data)

    # Sort by park name
    parks_list.sort(key=lambda x: x["park_name"])
    return parks_list

def main():
    # Fetch all parks from API
    raw_data = fetch_all_parks()

    # Aggregate duplicates
    print("Aggregating duplicate park entries...")
    aggregated = aggregate_parks(raw_data)
    print(f"Aggregated into {len(aggregated)} unique parks")

    # Save to JSON
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(aggregated, f, indent=2)

    print(f"\nDone! Created {OUTPUT_FILE} with {len(aggregated)} parks")

    # Show sample
    print("\nSample parks:")
    for park in aggregated[:5]:
        features_count = len(park['amenities']['special_features'])
        print(f"  - {park['park_name']}: {features_count} special features, best for: {', '.join(park['best_for'][:2])}")

if __name__ == "__main__":
    main()
