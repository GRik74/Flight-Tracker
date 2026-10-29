from Aircraft.tracker import AircraftTracker
from adsb_reader import load_aircraft
from output import show_planes, write_output, dump_error_info
from time import sleep, monotonic
import select
import sys


DEBUG = True
if DEBUG: import os

def main():
    tracker = AircraftTracker()
    try:
        _run(tracker)
    except Exception as error:
        dump_error_info(error, "Unhandled main-loop failure", severity="CRITICAL",
                        handled=False, tracked_planes=tracker.tracked_planes)
        raise


def _run(tracker):
    # ACTIVE = True

    interval = 1.0
    cycles_left = None
    plane_output_mode = "default"

################# START MAIN PROGRAM LOOP #########################

    while True:
        try:
            aircraft = load_aircraft()
            if not isinstance(aircraft, list):
                raise ValueError("Receiver aircraft field must be a list")
        except (OSError, ValueError) as error:
            dump_error_info(error, "Reading receiver snapshot; retrying next interval",
                            severity="WARNING", tracked_planes=tracker.tracked_planes)
            sleep(interval)
            continue
        if DEBUG:os.system("clear")

        tracker.update_tracked_planes(aircraft)
        write_output([p for p in tracker.current_planes
                      if p.interesting in tracker.interesting_states], tracker.tracked_planes)

        print(f"Aircraft heard: {len(aircraft)} | Tracked planes: {len(tracker.tracked_planes)}")

        positioned_planes = [plane for plane in tracker.active if plane.distance_available and isinstance(plane.dist_nm, (int, float))]
        print(f"Non-suppressed aircraft with known positions: {len(positioned_planes)}\n\n")

        if plane_output_mode == "default":
            planes_interesting = [plane for plane in tracker.current_planes if plane.interesting in tracker.interesting_states]
            if len(planes_interesting) == 0:
                print("No interesting planes found... Checking for watchlist planes...\n\n")
                planes_interesting = [plane for plane in tracker.current_planes if plane.interesting == tracker.watchlist_state]
                
            if len(planes_interesting) == 0 and len(positioned_planes) > 0:
                print("No interesting/watchlist planes found... Finding the closest plane instead...\n\n")
                closest_plane = min(positioned_planes, key=lambda plane: plane.dist_nm)
                show_planes([closest_plane])
            else:
                print(f"Tracked planes with potentially interesting status: {len(planes_interesting)}")
                show_planes(planes_interesting)

        elif plane_output_mode == "all":
            print(f"Plane output mode set to all - showing all heard aircraft...")
            show_planes(positioned_planes)

        elif plane_output_mode == "suppressed":
            planes_suppressed = [plane for plane in positioned_planes if plane.interesting in tracker.suppressed_states]
            if len(planes_suppressed) != 0:
                print("Plane output mode set to suppressed - showing all suppressed aircraft with available position data.")
                show_planes(planes_suppressed)
            else:
                print("Plane output mode set to suppressed, but no suppressed planes in tracker. Resetting output mode to default.")
                plane_output_mode = "default"


        if DEBUG:
            print(f"\nDEBUG: Tracked planes this cycle: {len(tracker.tracked_planes)}")
            oldest_plane = max(tracker.tracked_planes.values(), key=lambda plane: plane.age, default=None)
            print(f"DEBUG: Oldest plane in tracked_planes: {oldest_plane.hex_code if oldest_plane else 'N/A'} (Age: {oldest_plane.age if oldest_plane else 'N/A'})")
            newest_plane = min(tracker.tracked_planes.values(), key=lambda plane: plane.age, default=None)
            print(f"DEBUG: Oldest plane in tracked_planes: {newest_plane.hex_code if newest_plane else 'N/A'} (Age: {newest_plane.age if newest_plane else 'N/A'})")

        if cycles_left is not None:
            cycles_left -= 1
            if cycles_left <= 0:
                more_cycles = input("No cycles left. Enter a new number of cycles, leave blank for indefinite running, or enter 'q' to exit:>").strip().lower()
                if isinstance(more_cycles, int()): cycles_left = int(more_cycles)
                elif more_cycles == "": cycles_left = None
                else: break

        deadline = monotonic() + interval                        

        sleep(interval)

        remaining = max(0, deadline - monotonic())
        ready, _, _ = select.select([sys.stdin], [], [], remaining)

        if ready:
            if sys.stdin.readline() == "":
                return

            print("Paused. Commands: interval N | cycles N | cycles all | output | resume | q")

            while True:
                command = input("paused> ").strip().lower().split()

                try:
                    match command:
                        case ["resume"]:
                            break

                        case["q"]:
                            return
                        
                        case ["interval", value]:
                            value = float(value)
                            if not 0.1 <= value <= 3600:
                                raise ValueError
                            interval = value
                            deadline = monotonic() + interval
                            print(f"Update pause: {interval:g} seconds")

                        case ["cycles", "all"]:
                            cycles_left = None
                            print("Running indefinitely")

                        case ["cycles", value]:
                            value = int(value)
                            if value < 1:
                                raise ValueError
                            cycles_left = value
                            print(f"Running {value} more updates")

                        case ["output", value]:

                            if value == "default" or value == "suppressed" or value == "all":
                                plane_output_mode = value
                                print(f"Changed output mode to {value}")
                            else:
                                raise TypeError

                        case _:
                            print("Use interval N, cycles N, cycles all, resume, output, or q.")

                except ValueError as error:
                    dump_error_info(error, "Invalid command", severity="INFO")
                    print("Use interval 0.1-3600 or a positive whole cycle count.")
                except TypeError as error:
                    dump_error_info(error, "Invalid output command", severity="INFO")
                    print("Valid output mode choices: default | suppressed | all.")


######################### END MAIN PROGRAM LOOP ###########################

if __name__ == "__main__":
    main()

