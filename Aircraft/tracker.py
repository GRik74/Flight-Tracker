# Create class AircraftTracker
# shift tracking/collection update/garbage collection to the class
from Aircraft.aircraft import Aircraft, Interesting

DEBUG = True
buffer_threshold = 30  # Grace cycles before stopping interest tracking or removing absent aircraft.

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
        self.current_codes = set()

    def update_tracked_planes(self, adsb_data):
        self.adsb_data = adsb_data
        self.current_planes = []
        self.active = []

        self.current_codes = get_current_hex_codes(self.adsb_data)

        for plane in self.adsb_data:
            hex_code = plane.get("hex")
            if not hex_code: continue
            if hex_code in self.tracked_planes:
                this_plane = self.tracked_planes[hex_code]
                this_plane.update(plane)
            else:
                this_plane = Aircraft(plane)

            self.update_plane_state(this_plane)
            self.tracked_planes[hex_code] = this_plane
            self.current_planes.append(this_plane)
            if this_plane.interesting != Interesting.STOP_TRACKING:
                self.active.append(this_plane)

        self.remove_stale_planes()

    def update_plane_state(self, plane):
        # Apply retention policy after the aircraft's current interest is calculated.
        if plane.interesting in self.interesting_states or plane.interesting == Interesting.WATCHLIST:
            plane.buffer_grace = 0
        elif plane.interesting != Interesting.STOP_TRACKING:
            if plane.buffer_grace >= buffer_threshold:
                plane.interesting = Interesting.STOP_TRACKING
            else:
                plane.buffer_grace += 1

    def remove_stale_planes(self):
        # Remove stale planes from tracked_planes
        for hex_code in list(self.tracked_planes.keys()):
            plane = self.tracked_planes[hex_code]
            if hex_code not in self.current_codes:
                if plane.missing_from_receiver >= buffer_threshold / 2:
                    del self.tracked_planes[hex_code]

                    if DEBUG:
                        print(f"DEBUG: Removed stale plane {hex_code} from tracked_planes.")
                else:
                    plane.missing_from_receiver += 1
                    if DEBUG:
                        print(f"DEBUG: Incremented missing from receiver for {hex_code} to {plane.missing_from_receiver}.")
            else:
                plane.missing_from_receiver = 0
