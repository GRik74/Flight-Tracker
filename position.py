from pathlib import Path
from math import radians, sin, cos, sqrt, atan2, degrees

LOCATION_FILE = Path("location.txt")

def load_home_pos():
    """
    Load the home position (latitude and longitude) from the location.txt file.
    Returns: A tuple containing the latitude and longitude as floats.
    """
    text = LOCATION_FILE.read_text(encoding="utf-8").strip()
    lat_text, lon_text = text.split(",")

    return float(lat_text), float(lon_text)


def distance_miles(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between point A and point B using the Haversine formula.
    Returns the distance in miles.
    """


    earth_radius_miles = 3958.8

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_miles * c

def get_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing from point A (lat1, lon1) to point B (lat2, lon2).
    Returns the bearing in degrees (0-360).
    """
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1

    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - (sin(lat1) * cos(lat2) * cos(dlon))

    initial_bearing = atan2(x, y)
    initial_bearing_degrees = degrees(initial_bearing)
    compass_bearing = (initial_bearing_degrees + 360) % 360

    return compass_bearing
    
    
def get_CPA(bearing, distance, track, speed):
    """
    Calculate closest point of approach and time to reach that point.
    
    Returns tuple of time (in hours) and distance to CPA (in that order).
    """
    
    b = radians(bearing)
    c = radians(track)
    
    x = distance * sin(b)
    y = distance * cos(b)
    
    vx = speed * sin(c)
    vy = speed * cos(c)
    
    t = -((x * vx) + (y * vy)) / ((vx**2) + (vy**2))
    D = ((x + (vx * t))**2 + (y + (vy * t))**2)
    
    return t, D
