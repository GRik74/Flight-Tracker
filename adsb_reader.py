import json
from pathlib import Path
from position import load_home_pos, get_CPA
from aircraft import Aircraft, Interesting

DEBUG = True
if DEBUG: import os
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
        if plane.distance_available: plane_info += f" | Dist.: {str(round(plane.dist_nm, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4}"
        if plane.relational_info_available: plane_info += f" | Track: {str(int(round(plane.track, 0))):>4}"
        plane_info += f" | Alt: {str(round(plane.alt_ft, 1)):>7} ft" if plane.altitude_available else f" | Alt: {'unknown':>7} ft"
        plane_info += f" | GS: {str(int(round(plane.speed_kts, 0))):>8} kts" if plane.groundspeed_available else f" | GS: {'unknown':>8} kts"

        print(plane_info)

def main():
    old_planes = []
    interesting_planes = []
    watchlist = []
    ACTIVE = True

    while ACTIVE:
        os.system("clear")
        aircraft = load_aircraft()
        planes = []

        print(f"Aircraft heard: {len(aircraft)}")
        
        for plane in aircraft:
            this_plane = Aircraft(plane)
            if this_plane.distance_available: planes.append(this_plane)

            if this_plane.interesting.value > 0:
                if this_plane not in interesting_planes:
                    interesting_planes.append(this_plane)
                    if this_plane in watchlist:
                        watchlist.remove(this_plane)
                else:
                    # Update the existing plane in interesting_planes with the new data
                    index = interesting_planes.index(this_plane)
                    interesting_planes[index].plane = this_plane.plane  # Update the plane data
                    interesting_planes[index].update()
            else:
                if this_plane in interesting_planes:
                    interesting_planes.remove(this_plane)
                if this_plane.interesting == Interesting.WATCHLIST:
                    if this_plane not in watchlist:
                        watchlist.append(this_plane)

        print(f"Aircraft with known positions: {len(planes)}")
        if len(interesting_planes) == 0:
            if planes:
                print("No interesting planes found... Finding the closest plane instead...\n")
                closest_plane = min(planes, key=lambda plane: plane.dist_nm if isinstance(plane.dist_nm, (int, float)) else float('inf'))
                show_planes([closest_plane])
            else:
                print("No planes with valid distance information found.")
        else:
            print(f"Found {len(interesting_planes)} interesting planes:\n")
            show_planes(interesting_planes)

        RUN_AGAIN = input("\nRun again? (y/n): ").strip().lower()
        ACTIVE = True if RUN_AGAIN != "n" else False



if __name__ == "__main__":
    main()