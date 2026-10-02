import json
from pathlib import Path
from position import load_home_pos, get_CPA
from aircraft import Aircraft, Interesting
from garbage_collection import get_current_hex_codes

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
        if DEBUG: print(f"-----------------------------\nDEBUG: {plane.hex_code} | Age: {plane.age} | Missing from receiver: {plane.missing_from_receiver} | Buffer grace: {plane.buffer_grace} | Interesting: {plane.interesting} | Score: {plane.debug_score:.2f} \n-----------------------------")

def main():
    tracked_planes = {}
    # interesting_planes = {}
    # watchlist = {}
    # buffer = {}
    buffer_threshold = 15
    interesting_states = [Interesting.INTERESTING, Interesting.VERY_INTERESTING]
    ACTIVE = True

################# START MAIN PROGRAM LOOP #########################

    while ACTIVE:
        aircraft = load_aircraft()
        planes = []
        planes_interesting = []
        hexes_to_remove = []
        if DEBUG:
            planes_removed_this_cycle, stale_planes_count, duplicate_hex_codes = 0, 0, 0
            os.system("clear")

        # Check for stale/duplicate codes
        current_codes = get_current_hex_codes(aircraft)

        print(f"Aircraft heard: {len(aircraft)}")
        
        for plane in aircraft:
            hex_code = plane.get("hex")
            if not hex_code: continue
            # Pull plane data from interesting_planes/watchlist if exists (preserves any persistent data) or create new instance
            # Update data if exists
            if hex_code in tracked_planes:
                this_plane = tracked_planes[hex_code]
                this_plane.update(plane)
            else:
                this_plane = Aircraft(plane)

            # if this_plane.distance_available and this_plane.interesting != Interesting.IGNORE: planes.append(this_plane)
            planes.append(this_plane)

            # Determine if plane needs to be updated, removed, or newly assigned
            if this_plane.interesting in interesting_states:
                this_plane.buffer_grace = 0
                tracked_planes[hex_code] = this_plane
                # interesting_planes[hex_code] = this_plane
                # if hex_code in watchlist: del watchlist[hex_code]
                # if hex_code in buffer: del buffer[hex_code]

            elif this_plane.interesting == Interesting.WATCHLIST:
                this_plane.buffer_grace = 0
                tracked_planes[hex_code] = this_plane
                # if hex_code in interesting_planes: del interesting_planes[hex_code]
                # if hex_code in buffer: del buffer[hex_code]

            elif this_plane.interesting == Interesting.IGNORE:
                if this_plane.buffer_grace >= buffer_threshold:
                    if hex_code in tracked_planes: del tracked_planes[hex_code]
                    if DEBUG: planes_removed_this_cycle += 1
                else:
                    this_plane.buffer_grace += 1
                    tracked_planes[hex_code] = this_plane

                # if hex_code in watchlist: del watchlist[hex_code]
                # if hex_code in interesting_planes: del interesting_planes[hex_code]
                # if hex_code in buffer: del buffer[hex_code]

            else:
                if this_plane.buffer_grace >= buffer_threshold:
                    if hex_code in tracked_planes: del tracked_planes[hex_code]
                    if DEBUG: planes_removed_this_cycle += 1
                else:
                    this_plane.buffer_grace += 1
                    tracked_planes[hex_code] = this_plane

        # Check for planes that are no longer being received and remove them if missing for buffer_threshold cycles; otherwise, increment their missing_from_receiver counter
        for tracked in tracked_planes.values():
            hex_code = tracked.hex_code
            if hex_code not in current_codes:
                if DEBUG: stale_planes_count += 1
                if tracked.missing_from_receiver >= buffer_threshold:
                    hexes_to_remove.append(hex_code)
                else:
                    tracked.missing_from_receiver += 1
            else:
                tracked.missing_from_receiver = 0

        if len(hexes_to_remove) > 0:
            for hex_code in hexes_to_remove:
                if hex_code in tracked_planes: del tracked_planes[hex_code]
                if DEBUG: planes_removed_this_cycle += 1

        positioned_planes = [plane for plane in planes if plane.distance_available]
        print(f"Aircraft with known positions: {len(positioned_planes)}")
        planes_interesting = [plane for plane in planes if plane.interesting in interesting_states]
        if len(planes_interesting) == 0 and len(planes) > 0:
            print("No interesting planes found... Finding the closest plane instead...\n")
            closest_plane = min(positioned_planes, key=lambda plane: plane.dist_nm if isinstance(plane.dist_nm, (int, float)) else float('inf'))
            show_planes([closest_plane])
        else:
            print(f"Tracked planes with potentially interesting status: {len(planes_interesting)}")
            show_planes(planes_interesting)

        if DEBUG:
            print(f"\nDEBUG: Tracked planes this cycle: {len(tracked_planes)}")
            print(f"\nDEBUG: Stale planes this cycle: {stale_planes_count}")
            print(f"DEBUG: Duplicate planes this cycle: {duplicate_hex_codes}")
            print(f"DEBUG: Planes removed this cycle: {planes_removed_this_cycle}")
            oldest_plane = max(tracked_planes.values(), key=lambda plane: plane.age, default=None)
            print(f"DEBUG: Oldest plane in tracked_planes: {oldest_plane.hex_code if oldest_plane else 'N/A'} (Age: {oldest_plane.age if oldest_plane else 'N/A'})")

        RUN_AGAIN = input("\nRun again? (y/n): ").strip().lower()
        ACTIVE = True if RUN_AGAIN != "n" else False

######################### END MAIN PROGRAM LOOP ###########################

if __name__ == "__main__":
    main()