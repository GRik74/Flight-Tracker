import position

class Aircraft():
    def __init__(self, plane_data):
        self.plane = plane_data
        self.hex_code = self.plane.get("hex", "unknown")
        self.flight = self.plane.get("flight", "").strip() or "unknown"
        self.altitude = self.plane.get("alt_baro", "unknown")
        self.groundspeed = self.plane.get("gs", "unknown")

        self.lat = self.plane.get("lat", "unknown")
        self.lon = self.plane.get("lon", "unknown")
        if self.lat != "unknown" and self.lon != "unknown":
            self.distance = position.distance_miles(position.home_lat, position.home_lon, self.lat, self.lon)
        else:
            self.distance = "unknown"

