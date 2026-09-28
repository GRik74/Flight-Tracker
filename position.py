from pathlib import Path
from math import radians, sin, cos, sqrt, atan2


LOCATION_FILE = Path("location.txt")

def load_home_pos():
    text = LOCATION_FILE.read_text(encoding="utf-8").strip()
    lat_text, lon_text = text.split(",")

    return float(lat_text), float(lon_text)


def distance_miles(lat1, lon1, lat2, lon2):
    earth_radius_miles = 3958.8

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(earth_radius_miles * c, 1)


home_lat, home_lon = load_home_pos()