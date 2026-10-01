import json
from pathlib import Path
from position import load_home_pos, get_CPA
from aircraft import Aircraft, Interesting
from garbage_collection import get_current_hex_codes, check_existing_hex_codes

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
        plane_info = f"Hex Code: {plane.hex_code:7}"
        plane_info += f"| {plane.flight:10}" if not plane.flight is None else ""
        if plane.distance_available: plane_info += f" | Dist.: {str(round(plane.dist_nm, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4}"
        if plane.relational_info_available: plane_info += f" | Track: {str(int(round(plane.track, 0))):>4}"
        plane_info += f" | Alt: {str(round(plane.alt_ft, 1)):>7} ft" if plane.altitude_available else f" | Alt: {'unknown':>7} ft"
        plane_info += f" | GS: {str(int(round(plane.speed_kts, 0))):>8} kts" if plane.groundspeed_available else f" | GS: {'unknown':>8} kts"

        print(plane_info)

def main():
    old_planes = {}
    interesting_planes = {}
    watchlist = {}
    buffer = {}
    buffer_threshold = 5
    interesting_states = [Interesting.INTERESTING, Interesting.VERY_INTERESTING]
    ACTIVE = True

################# START MAIN PROGRAM LOOP #########################

    while ACTIVE:
        os.system("clear")
        aircraft = load_aircraft()
        planes = []
        stale_codes, duplicate_codes = [], []
        stale_planes, duplicate_planes = {}, {}

        # Check for stale/duplicate codes
        current_codes = get_current_hex_codes(aircraft)
        if len(old_planes) > 0:
            stale_codes, duplicate_codes = check_existing_hex_codes([watchlist, interesting_planes, buffer], current_codes)
            if not stale_codes is None and len(stale_codes) > 0:
                print(f"Found {len(stale_codes)} stale hex codes:")
                for code in stale_codes:
                    if code in old_planes: stale_planes[code] = old_planes[code]
                show_planes(stale_planes.values())

            if not duplicate_codes is None and len(duplicate_codes) > 0:
                print(f"Found {len(duplicate_codes)} duplicate hex codes:")
                for code in duplicate_codes:
                    if code in old_planes: duplicate_planes[code] = old_planes[code]
                show_planes(duplicate_planes.values())


        print(f"Aircraft heard: {len(aircraft)}")
        
        for plane in aircraft:
            hex_code = plane.get("hex")
            if not hex_code: continue
            # Pull plane data from interesting_planes/watchlist if exists (preserves any persistent data) or create new instance
            # Update data if exists
            if hex_code in interesting_planes:
                this_plane = interesting_planes[hex_code]
                this_plane.update(plane)
            elif hex_code in watchlist:
                this_plane = watchlist[hex_code]
                this_plane.update(plane)
            elif hex_code in buffer:
                this_plane = buffer[hex_code]
                this_plane.update(plane)
            else:
                this_plane = Aircraft(plane)

            # if this_plane.distance_available and this_plane.interesting != Interesting.IGNORE: planes.append(this_plane)
            planes.append(this_plane)

            # Determine if plane needs to be promoted, demoted, removed, or newly assigned
            if this_plane.interesting in interesting_states:
                interesting_planes[hex_code] = this_plane
                if hex_code in watchlist: del watchlist[hex_code]
                if hex_code in buffer: del buffer[hex_code]

            elif this_plane.interesting == Interesting.WATCHLIST:
                watchlist[hex_code] = this_plane
                if hex_code in interesting_planes: del interesting_planes[hex_code]
                if hex_code in buffer: del buffer[hex_code]

            elif this_plane.interesting == Interesting.IGNORE:
                if hex_code in watchlist: del watchlist[hex_code]
                if hex_code in interesting_planes: del interesting_planes[hex_code]
                if hex_code in buffer: del buffer[hex_code]

            else:
                if hex_code in buffer:
                    buffer[hex_code] = this_plane
                    if buffer[hex_code].buffer_grace >= buffer_threshold:
                        del buffer[hex_code]
                    else:
                        buffer[hex_code].buffer_grace += 1
                else:
                    this_plane.buffer_grace = 0
                    buffer[hex_code] = this_plane
                    if hex_code in interesting_planes: del interesting_planes[hex_code]
                    if hex_code in watchlist: del watchlist[hex_code]

            if hex_code in buffer and (hex_code in interesting_planes or hex_code in watchlist): del buffer[hex_code]

        print(f"Aircraft with known positions: {len(planes)}")
        if len(interesting_planes) == 0:
            if len(watchlist) != 0:
                print(f"No interesting planes found... Found {len(watchlist)} planes worth watching:\n")
                show_planes(watchlist.values())
            elif planes:
                print("No interesting planes found... Finding the closest plane instead...\n")
                closest_plane = min(planes, key=lambda plane: plane.dist_nm if isinstance(plane.dist_nm, (int, float)) else float('inf'))
                show_planes([closest_plane])
            else:
                print("No planes with valid distance information found.")
        else:
            print(f"Found {len(interesting_planes)} interesting planes:\n")
            show_planes(interesting_planes.values())
        

        RUN_AGAIN = input("\nRun again? (y/n): ").strip().lower()
        ACTIVE = True if RUN_AGAIN != "n" else False

        for d in [interesting_planes, watchlist, buffer]:
            for hex in d.keys():
                if not hex in old_planes:
                    if hex in stale_planes.keys():
                        print("stale")
                    old_planes[hex] = d[hex]

######################### END MAIN PROGRAM LOOP ###########################

if __name__ == "__main__":
    main()