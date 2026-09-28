import json
from pathlib import Path
from position import load_home_pos, distance_miles
from aircraft import Aircraft


AIRCRAFT_FILE = Path("/run/dump1090-fa/aircraft.json")
home_lat, home_lon = load_home_pos()

def load_aircraft():
    with AIRCRAFT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

        return data.get("aircraft", [])


def main():
    aircraft = load_aircraft()
    planes = []
    interesting_planes = []

    print(f"Aircraft currently tracked: {len(aircraft)}")



    for plane in aircraft:
        this_plane = Aircraft(plane, home_lat, home_lon)
        if isinstance(this_plane.distance, (int, float)): planes.append(this_plane)
        if this_plane.is_interesting: interesting_planes.append(this_plane)

    if len(interesting_planes) == 0:
        if planes:
            print("No interesting planes found... Finding the closest plane instead...\n")
            closest_plane = min(planes, key=lambda plane: plane.distance if isinstance(plane.distance, (int, float)) else float('inf'))
            print(f"Closest plane: {closest_plane.flight} | Distance: {closest_plane.distance} mi. | Altitude: {closest_plane.altitude} | Groundspeed: {closest_plane.groundspeed} kts")
        else:
            print("No planes with valid distance information found.")
    else:
        print(f"Found {len(interesting_planes)} interesting planes:\n")
        for plane in interesting_planes:
            print(
                f"{plane.flight:10} | ICAO: {plane.hex_code:6} | Alt: {str(plane.altitude):>7} | GS: {str(plane.groundspeed):>8} kts | "
                f"Dist (mi.): {str(plane.distance):>8}"
            )



if __name__ == "__main__":
    main()