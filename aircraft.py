import position

class Aircraft():
    def __init__(self, plane_data, home_lat, home_lon):
        self.plane = plane_data
        self.hex_code = self.plane.get("hex", "unknown")
        self.flight = self.plane.get("flight", "").strip() or "unknown"
        self.altitude = self.plane.get("alt_baro", "unknown")
        self.groundspeed = self.plane.get("gs", "unknown")

        self.lat = self.plane.get("lat", "unknown")
        self.lon = self.plane.get("lon", "unknown")
        if self.lat != "unknown" and self.lon != "unknown":
            self.distance = position.distance_miles(home_lat, home_lon, self.lat, self.lon)
        else:
            self.distance = "unknown"

        self.is_interesting = False
        if self.distance != "unknown":
            if self.distance <= 5:
                self.is_interesting = True
            elif self.distance <= 15 and isinstance(self.altitude, (int, float)) and self.altitude < 15000:
                self.is_interesting = True
