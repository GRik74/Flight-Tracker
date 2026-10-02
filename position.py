from pathlib import Path
from math import asin, radians, sin, cos, sqrt, atan2, degrees

LOCATION_FILE = Path("location.txt")

def load_home_pos():
    """
    Load the home position (latitude and longitude) from the location.txt file.
    Returns: A tuple containing the latitude and longitude as floats.
    """
    text = LOCATION_FILE.read_text(encoding="utf-8").strip()
    lat_text, lon_text = text.split(",")

    return float(lat_text), float(lon_text)


def distance_nm(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between point A and point B using the Haversine formula.

    Returns the distance in nautical miles.
    """


    earth_radius_nm = 3440.065

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_nm * c

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
    
def estimate_new_position(lat, lon, track, speed_kts, time_elapsed_sec):
    """
    Estimate the new position of an aircraft given its last known position, track, speed, and time elapsed since position last known.

    Returns a tuple containing the new latitude and longitude.
    """
    distance_nm = (speed_kts * time_elapsed_sec) / 3600.0  # Convert speed to nautical miles per second

    lat = radians(lat)
    lon = radians(lon)
    track = radians(track)

    earth_radius_nm = 3440.065

    new_lat = asin(sin(lat) * cos(distance_nm / earth_radius_nm) +
                   cos(lat) * sin(distance_nm / earth_radius_nm) * cos(track))

    new_lon = lon + atan2(sin(track) * sin(distance_nm / earth_radius_nm) * cos(lat),
                          cos(distance_nm / earth_radius_nm) - sin(lat) * sin(new_lat))

    return degrees(new_lat), degrees(new_lon)

def get_CPA(bearing, dist_nm, track, speed_kts):
    """
    Calculate closest point of approach and time to reach that point.
    
    Returns tuple of time (hours), distance (nautical miles), and bearing from house to plane (degrees 0-360) at CPA (in that order).
    """

    if speed_kts == 0:
        return None, None, None

    # Use vector math to calculate distance and time to closest point of approach (CPA)
    b = radians(bearing)
    c = radians(track)
    
    x = dist_nm * sin(b)
    y = dist_nm * cos(b)

    vx = speed_kts * sin(c)
    vy = speed_kts * cos(c)

    # t < 0 indicates that the closest point of approach has already occurred
    # t == 0 indicates that CPA is right now
    time_to_CPA = -((x * vx) + (y * vy)) / ((vx**2) + (vy**2))
    dist_nm_at_CPA = sqrt((x + (vx * time_to_CPA))**2 + (y + (vy * time_to_CPA))**2)

    # Find the bearing to the CPA point by calculating CPA coordinates and finding the bearing angle of them
    x_cpa = x + (vx * time_to_CPA)
    y_cpa = y + (vy * time_to_CPA)

    bearing_at_CPA = (degrees(atan2(x_cpa, y_cpa)) + 360) % 360
    
    return time_to_CPA, dist_nm_at_CPA, bearing_at_CPA
