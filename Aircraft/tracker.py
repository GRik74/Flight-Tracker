# Create class AircraftTracker
# shift tracking/collection update/garbage collection to the class
from Aircraft.aircraft import Aircraft, Interesting
from output import dump_error_info
from copy import deepcopy

DEBUG = True
interest_grace = 45  # Grace cycles before stopping interest tracking.
missing_grace = 30 # Grace cycles before stale aircraft are removed from tracked_planes.

def get_current_hex_codes(planes):
    codes = {
        plane.get("hex")
        for plane in planes
        if plane.get("hex")
    }

    return codes


class AircraftTracker:
    def __init__(self):
        self.adsb_data = []
        self.tracked_planes = {}
        self.current_planes = []
        self.active = []
        self.interesting_states = [Interesting.INTERESTING, Interesting.VERY_INTERESTING]
        self.watchlist_state = Interesting.WATCHLIST
        self.suppressed_states = [Interesting.STOP_TRACKING, Interesting.IGNORE]
        self.current_codes = set()

    def update_tracked_planes(self, adsb_data):
        valid = []
        for row in adsb_data:
            if isinstance(row, dict) and isinstance(row.get("hex", ""), str):
                valid.append(row)
            else:
                dump_error_info(ValueError("Invalid aircraft record"), repr(row),
                                severity="WARNING", tracked_planes=self.tracked_planes)
        self.adsb_data = valid
        self.current_planes = []
        self.active = []

        self.current_codes = get_current_hex_codes(self.adsb_data)

        for plane in self.adsb_data:
            hex_code = plane.get("hex")
            if not hex_code: continue
            this_plane = self.tracked_planes.get(hex_code)
            previous = deepcopy(vars(this_plane)) if this_plane is not None else None
            try:
                if this_plane is None:
                    this_plane = Aircraft(plane)
                else:
                    this_plane.update(plane)
                self.update_plane_state(this_plane)
            except (ValueError, TypeError, ArithmeticError, KeyError) as error:
                if previous is not None:
                    vars(this_plane).clear()
                    vars(this_plane).update(previous)
                dump_error_info(error, f"Processing aircraft {hex_code}: {plane!r}",
                                severity="ERROR", tracked_planes=self.tracked_planes)
                continue
            self.tracked_planes[hex_code] = this_plane
            self.current_planes.append(this_plane)
            if this_plane.interesting != Interesting.STOP_TRACKING:
                self.active.append(this_plane)

        self.remove_stale_planes()

    def update_plane_state(self, plane):
        # Apply retention policy after the aircraft's current interest is calculated.
        if plane.interesting in self.interesting_states or plane.interesting == Interesting.WATCHLIST:
            if plane.buffer_grace != 0 and DEBUG:
                print(f"DEBUG: Reset interesting buffer for {plane.hex_code} to 0. Current state: {plane.interesting}.")
            plane.buffer_grace = 0
        elif plane.interesting != Interesting.STOP_TRACKING:
            if plane.buffer_grace >= interest_grace:
                plane.stop_tracking()
                if DEBUG:
                    print(f"DEBUG: Stopped tracking {plane.hex_code} due to expired grace period.")
            else:
                plane.buffer_grace += 1
                # if DEBUG:
                #     print(f"DEBUG: Incremented interesting buffer for {plane.hex_code} to {plane.buffer_grace}.")

    def remove_stale_planes(self):
        # Remove stale planes from tracked_planes
        for hex_code in list(self.tracked_planes.keys()):
            plane = self.tracked_planes[hex_code]
            if hex_code not in self.current_codes:
                if plane.missing_from_receiver >= missing_grace:
                    del self.tracked_planes[hex_code]

                    if DEBUG:
                        print(f"DEBUG: Removed stale plane {hex_code} from tracked_planes.")
                else:
                    plane.missing_from_receiver += 1
                    if DEBUG:
                        print(f"DEBUG: Incremented missing from receiver for {hex_code} to {plane.missing_from_receiver}.")
            else:
                if plane.missing_from_receiver != 0 and DEBUG:
                    print(f"DEBUG: Reset missing from receiver counter for {hex_code} to 0.")

                plane.missing_from_receiver = 0

