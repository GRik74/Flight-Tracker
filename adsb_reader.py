import json
from pathlib import Path
from position import *
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
        if this_plane.distance != "unknown" and (this_plane.distance <= 5 or (this_plane.distance <= 15 and this_plane.altitude < 15000)):
            interesting_planes.append(this_plane)

    if len(interesting_planes) == 0:
        print("No interesting planes found.")
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