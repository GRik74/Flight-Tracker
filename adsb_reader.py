import json
from pathlib import Path
from position import load_home_pos
from aircraft import Aircraft
# from math import round


AIRCRAFT_FILE = Path("/run/dump1090-fa/aircraft.json")
home_lat, home_lon = load_home_pos()

def load_aircraft():
    with AIRCRAFT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

        return data.get("aircraft", [])


def show_planes(planes):
    for plane in planes:
        print(
            f"{plane.flight:10} | Dist.: {str(round(plane.distance, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4} | Heading: {str(int(round(plane.heading, 0))):>4} | Alt: {str(round(plane.altitude, 1)):>7} | GS: {str(int(round(plane.groundspeed, 0))):>5} kts"
        )


def main():
    aircraft = load_aircraft()
    planes = []
    interesting_planes = []
    watchlist = []

    print(f"Aircraft heard: {len(aircraft)}")



    for plane in aircraft:
        this_plane = Aircraft(plane, home_lat, home_lon)
        if isinstance(this_plane.distance, (int, float)): planes.append(this_plane)
        if this_plane.is_interesting: interesting_planes.append(this_plane)

    print(f"Aircraft with known positions: {len(planes)}")
    if len(interesting_planes) == 0:
        if planes:
            print("No interesting planes found... Finding the closest plane instead...\n")
            closest_plane = min(planes, key=lambda plane: plane.distance if isinstance(plane.distance, (int, float)) else float('inf'))
            show_planes([closest_plane])
        else:
            print("No planes with valid distance information found.")
    else:
        print(f"Found {len(interesting_planes)} interesting planes:\n")
        show_planes(interesting_planes)



if __name__ == "__main__":
    main()