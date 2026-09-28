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
    print()

    

    for plane in aircraft:
        this_plane = Aircraft(plane, home_lat, home_lon)
        planes.append(this_plane)
        if this_plane.is_interesting: interesting_planes.append(this_plane)

    if len(interesting_planes) == 0:
        print("No interesting planes found.")
        closest_plane = min(planes, key=lambda p: p.distance if isinstance(p.distance, (int, float)) else float('inf'))
        print(f"Closest plane: {closest_plane.flight} | Distance: {closest_plane.distance} mi. | Altitude: {closest_plane.altitude} | Groundspeed: {closest_plane.groundspeed} kts")

    else:
        for plane in interesting_planes:
            print(
                f"{plane.flight:10}  "
                f"ICAO: {plane.hex_code:6}  "
                f"Alt: {str(plane.altitude):>7}  "
                f"GS: {str(plane.groundspeed):>8} kts  "
                f"Dist (mi.): {str(plane.distance):>8}"
            )



if __name__ == "__main__":
    main()