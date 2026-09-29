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
        plane_info = f"{plane.flight:10}"
        if plane.distance_available: plane_info += f" | Dist.: {str(round(plane.distance, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4}"
        if plane.relational_info_available: plane_info += f" | Track: {str(int(round(plane.track, 0))):>4}"
        plane_info += f" | Alt: {str(round(plane.altitude, 1)):>7} ft" if plane.altitude_available else f" | Alt: {'unknown':>7} ft"
        plane_info += f" | GS: {str(int(round(plane.groundspeed, 0))):>8} kts" if plane.groundspeed_available else f" | GS: {'unknown':>8} kts"

        print(plane_info)

        # print(
        #     f"{plane.flight:10} | Dist.: {str(round(plane.distance, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4} | Track: {str(int(round(plane.track, 0))):>4} | Alt: {str(round(plane.altitude, 1)):>7} | GS: {str(int(round(plane.groundspeed, 0))):>8} kts"
        # )


def main():
    aircraft = load_aircraft()
    planes = []
    interesting_planes = []
    watchlist = []

    print(f"Aircraft heard: {len(aircraft)}")



    for plane in aircraft:
        this_plane = Aircraft(plane, home_lat, home_lon)
        if this_plane.distance_available: planes.append(this_plane)
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