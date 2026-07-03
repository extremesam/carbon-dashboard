import random

def geocode_address(address):
    # Replace with real geocoder (Nominatim / Mapbox later)
    return (
        6.5244 + random.uniform(-0.1, 0.1),
        3.3792 + random.uniform(-0.1, 0.1)
    )

def estimate_carbon_risk(lat, lon):
    # Simple placeholder logic
    score = (abs(lat) + abs(lon)) % 1

    if score < 0.33:
        return "low"
    elif score < 0.66:
        return "medium"
    return "high"
