from position import distance_miles

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

        self.heading = self.plane.get("track", "unknown")
        self.emergency = self.plane.get("emergency", "unknown")

        self.is_interesting = self.determine_interesting()


    def determine_interesting(self):
        """
            Run various methods related to position to get distance, closest approach, change in alt/speed, etc. to determine whether the plane is (or may become) interesting.
                -For each plane, assign a value for each 'interesting' attribute (from 0.0 to 10.0) that will sum to determine whether the plane is interesting, remains interesting, goes into watchlist, or isn't interesting at all
                -Planes with closest approach > 15 miles or (alt > 25000 and closest approach > 5 miles) are assigned 0.0 regardless of any other attributes
        """
        
        
        if self.distance != "unknown":
            if self.distance <= 5:
                return True
            elif self.distance <= 15 and isinstance(self.altitude, (int, float)) and self.altitude < 15000:# and is_closing
                return True
            elif self.emergency != "unknown" and self.emergency != "none" and self.emergency is not None:
                return True
            elif isinstance(self.groundspeed, (int, float):
                if self.groundspeed < 200 and self.distance < 8:# and is_closing
                    return True
                elif self.groundspeed > 600:# and is_closing
                    return True
            
        return False

    
    # def get_rate_of_close(self):


    # def get_rate_of_climb(self):


    # def get_eta_nearest_point(self):


    # def potentially_interesting(self):



