# Create class AircraftTracker
# shift tracking/collection update/garbage collection to the class
from Aircraft.aircraft import Aircraft, Interesting, buffer_threshold

DEBUG = True

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
        self.interesting_states = [Interesting.INTERESTING, Interesting.VERY_INTERESTING]
        self.current_codes = []

    def update_tracked_planes(self, adsb_data):
        self.adsb_data = adsb_data
        total_planes_heard = len(adsb_data)

        self.current_codes = get_current_hex_codes(self.adsb_data)

        for plane in self.adsb_data:
            hex_code = plane.get("hex")
            if not hex_code: continue
            if hex_code in self.tracked_planes:
                this_plane = self.tracked_planes[hex_code]
                this_plane.update(plane)
            else:
                this_plane = Aircraft(plane)

        self.remove_stale_planes()

        # return self.adsb_data, len(self.tracked_planes)



    def remove_stale_planes(self):
        # Remove stale planes from tracked_planes
        for hex_code in list(self.tracked_planes.keys()):
            if hex_code not in self.current_codes:
                plane = self.tracked_planes[hex_code]
                if plane.buffer_grace >= buffer_threshold:
                    del self.tracked_planes[hex_code]

                    if DEBUG:
                        print(f"DEBUG: Removed stale plane {hex_code} from tracked_planes.")
                else:
                    plane.buffer_grace += 1
                    if DEBUG:
                        print(f"DEBUG: Incremented buffer grace for {hex_code} to {plane.buffer_grace}.")

        
