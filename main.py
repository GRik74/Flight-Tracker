from Aircraft.tracker import AircraftTracker
from adsb_reader import load_aircraft
from output import show_planes

DEBUG = True
if DEBUG: import os

def main():
    tracker = AircraftTracker()
    ACTIVE = True

################# START MAIN PROGRAM LOOP #########################

    while ACTIVE:
        aircraft = load_aircraft()
        if DEBUG:os.system("clear")

        tracker.update_tracked_planes(aircraft)

        print(f"Aircraft heard: {len(aircraft)} | Tracked planes: {len(tracker.tracked_planes)}")

        positioned_planes = [plane for plane in tracker.current_planes if plane.distance_available and isinstance(plane.dist_nm, (int, float))]
        print(f"Aircraft with known positions: {len(positioned_planes)}")
        planes_interesting = [plane for plane in tracker.current_planes if plane.interesting in tracker.interesting_states]
        if len(planes_interesting) == 0 and len(positioned_planes) > 0:
            print("No interesting planes found... Finding the closest plane instead...\n")
            closest_plane = min(positioned_planes, key=lambda plane: plane.dist_nm)
            show_planes([closest_plane])
        else:
            print(f"Tracked planes with potentially interesting status: {len(planes_interesting)}")
            show_planes(planes_interesting)

        if DEBUG:
            print(f"\nDEBUG: Tracked planes this cycle: {len(tracker.tracked_planes)}")
            # print(f"\nDEBUG: Stale planes this cycle: {tracker.stale_planes_count}")
            # print(f"DEBUG: Duplicate planes this cycle: {tracker.duplicate_hex_codes}")
            # print(f"DEBUG: Planes removed this cycle: {tracker.planes_removed_this_cycle}")
            oldest_plane = max(tracker.tracked_planes.values(), key=lambda plane: plane.age, default=None)
            print(f"DEBUG: Oldest plane in tracked_planes: {oldest_plane.hex_code if oldest_plane else 'N/A'} (Age: {oldest_plane.age if oldest_plane else 'N/A'})")

        RUN_AGAIN = input("\nRun again? (y/n): ").strip().lower()
        ACTIVE = True if RUN_AGAIN != "n" else False

######################### END MAIN PROGRAM LOOP ###########################

if __name__ == "__main__":
    main()
