from position import distance_miles, get_bearing

class Aircraft():
    def __init__(self, plane_data, home_lat, home_lon):
        self.plane = plane_data
        self.hex_code = self.plane.get("hex", "unknown")
        self.flight = self.plane.get("flight", "").strip() or "unknown"
        self.altitude = self.plane.get("alt_baro", "unknown")
        self.groundspeed = self.plane.get("gs", "unknown")
        self.heading = self.plane.get("track", "unknown")

        self.lat = self.plane.get("lat", "unknown")
        self.lon = self.plane.get("lon", "unknown")

        self.distance = 0.0
        self.bearing_to_plane = 0.0
        self.recip_bearing = 0.0
        self.angle_on_bow = 0.0

        self.distance_available = True if self.lat != "unknown" and self.lon != "unknown" else False
        self.relational_info_available = True if self.distance_available and isinstance(self.heading, (int, float)) else False

        if self.distance_available:
            self.get_relational_info(home_lat, home_lon)

        # if self.lat != "unknown" and self.lon != "unknown":
        #     self.distance_available = True
            # self.distance = distance_miles(home_lat, home_lon, self.lat, self.lon)
            # self.bearing_to_plane = get_bearing(home_lat, home_lon, self.lat, self.lon)
            # self.recip_bearing = self.bearing_to_plane - 180 if self.bearing_to_plane > 180 else self.bearing_to_plane + 180

            # if self.heading != "unknown":
            #     self.relational_info_available = True
            # else:
            #     self.relational_info_available = False


            # self.angle_on_bow = self.heading - self.recip_bearing
            # if self.angle_on_bow < 0:
            #     self.angle_on_bow += 360

        # else:
        #     self.distance_available = False
        #     self.relational_info_available = False

        self.emergency = self.plane.get("emergency", "unknown")

        self.is_interesting = self.determine_interesting()


    def determine_interesting(self):
        """
            Current Function: Determines whether a plane is interesting based on decision tree.
            
            Returns boolean to indicate interesting/not interesting.

            
            Planned Function:
                Run various methods related to position to get distance, closest approach, change in alt/speed, etc. to determine whether the plane is (or may become) interesting.
                    -For each plane, assign a value for each 'interesting' attribute (from 0.0 to 10.0) that will sum to determine whether the plane is interesting, remains interesting, goes into watchlist, or isn't interesting at all
                    -Average values for certain categories of attributes with appropriate weight, sum all category averages, possibly use multipliers or 'bonus' points based on certain attributes
                    -Planes with closest approach > 15 miles or (alt > 25000 and closest approach > 5 miles) are assigned 0.0 (not interesting/impossible to become interesting) regardless of any other attributes
                    -Enum for interesting-ness: create a class to hold the enum values for interesting-ness (can't become interesting, not currently interesting, watchlist, interesting, very interesting) and assign interesting-ness state
                    -Latch interesting-ness state once threshold for 'interesting' passed, don't reset/downgrade state until interesting-ness score falls below some threshold to avoid repeated state flip-flops
        """
        
        
        if self.distance_available:
            if self.distance <= 5:
                return True
            elif self.distance <= 15 and isinstance(self.altitude, (int, float)) and self.altitude < 15000:# and is_closing
                return True
            elif self.emergency != "unknown" and self.emergency != "none" and self.emergency is not None:
                return True
            elif isinstance(self.groundspeed, (int, float)):
                if self.groundspeed < 200 and self.distance < 8:# and is_closing
                    return True
                elif self.groundspeed > 600:# and is_closing
                    return True
            
        return False

    

    def get_relational_info(self, home_lat, home_lon):
        """Sets relational information about the plane (distance, bearing, angle on bow, etc.) if available. If not available, sets relational_info_available to False."""
        self.distance = distance_miles(home_lat, home_lon, self.lat, self.lon)
        self.bearing_to_plane = get_bearing(home_lat, home_lon, self.lat, self.lon)
        self.recip_bearing = self.bearing_to_plane - 180 if self.bearing_to_plane > 180 else self.bearing_to_plane + 180

        if self.relational_info_available:
            self.angle_on_bow = self.heading - self.recip_bearing
            if self.angle_on_bow < 0:
                self.angle_on_bow += 360

    # def get_rate_of_close(self):


    # def get_rate_of_climb(self):


    # def get_eta_nearest_point(self):


    # def potentially_interesting(self):



