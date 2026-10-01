from position import distance_nm, get_bearing, get_CPA, load_home_pos
from enum import Enum

home_lat, home_lon = load_home_pos()

class Aircraft():
    def __init__(self, plane_data):
        self.hex_code = plane_data.get("hex", "unknown")
        self.LATCHED_NOT_INTERESTING = False
        self.LATCHED_INTERESTING = False
        self.interesting = Interesting.NOT_INTERESTING
        
        self.flight = None
        self.alt_ft = None
        self.speed_kts = None
        self.track = None
        self.emergency = None
        self.lat = None
        self.lon = None
        
        self.altitude_available = None
        self.groundspeed_available = None
        self.distance_available = None
        self.relational_info_available = None

        self.dist_nm = None
        self.bearing_to_plane = None
        self.recip_bearing = None
        self.angle_on_bow = None
        self.relative_bearing = None
        self.is_closing = None
        self.closest_point_of_approach = {'time_hr': None, 'dist_nm': None, 'bearing': None}
       
        self.is_interesting = False
        self.buffer_grace = 0
    
        self.update(plane_data, persistent=False)
        


    def update(self, plane_data, persistent=True):
        """
        Main update method. Calls all individual update methods as required.
        """
        
        if persistent: self.old_plane = self.plane
        self.plane = plane_data
        
        self.update_adsb_values()
        if self.distance_available:
            self.update_relational_info()
            
        self.is_interesting = self.update_interesting()
        
        
    def update_adsb_values(self):
        if self.flight is None:
            self.flight = self.plane.get("flight")
            self.flight = self.flight.strip() if isinstance(self.flight, str) else None
            
        self.alt_ft = self.plane.get("alt_baro")
        self.speed_kts = self.plane.get("gs")
        self.track = self.plane.get("track")
        self.emergency = self.plane.get("emergency")
        self.lat = self.plane.get("lat")
        self.lon = self.plane.get("lon")
        
        self.altitude_available = True if self.alt_ft is not None else False
        self.groundspeed_available = True if self.speed_kts is not None else False
        self.distance_available = True if self.lat is not None and self.lon is not None else False
        self.relational_info_available = True if self.distance_available and self.track is not None else False
        
    


    def update_interesting(self, persistent=True):
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
        
        if self.interesting == Interesting.IGNORE: return False

        ### Immediate disqualifiers - if any of these are true, the plane will most likely never become interesting and will be ignored
        if not self.is_closing and (self.dist_nm > 10 or self.alt_ft > 25000):
            self.interesting = Interesting.IGNORE
            return False

        ##### Algorithm - Not fully implemented yet, only sets Interesting enum value #####

        # Positional factors - where it is
        dist_factor = max((20.0 - self.dist_nm), 0.0) * 0.5 if self.distance_available else 0.0
        alt_factor = max((25000 - self.alt_ft)/2000, 0.0) * 0.2 if self.altitude_available else 0.0
        aob_factor = ((90 - self.angle_on_bow)/9) * 0.3 if self.relational_info_available else 0.0
        
        pos_factors = (dist_factor + alt_factor + aob_factor) * 0.8


        # Behavioral factors - what it's doing
        speed_factor = max((600 - self.speed_kts)/60, 0.0) * 0.1 if self.groundspeed_available else 0.0
        
        behavioral_factors = (speed_factor) * 0.2


        # Bonuses and special cases - things that make it more interesting than it would otherwise be
        emergency_bonus = ((dist_factor/10) + 1) if self.emergency != "unknown" and self.emergency != "none" and self.emergency is not None else 0.0
        
        bonus_factors = (emergency_bonus)
        
        
        # Multipliers - things that have a non-linear effect on how interesting the plane might be
        very_low_alt_mult = 1 + ((5000 - self.alt_ft) * 0.00002) if self.alt_ft < 5000 else 1.0
        
        
        # State Assignment
        base_score = (pos_factors + behavioral_factors + bonus_factors)
        score = min((base_score * very_low_alt_mult), 30)
        debug_score = base_score * very_low_alt_mult
        
        
        if score < 5:
            self.interesting = Interesting.IGNORE
            return False
        elif score < 10:
            self.interesting = Interesting.NOT_INTERESTING
            self.LATCHED_NOT_INTERESTING = True
            self.LATCHED_INTERESTING = False
        elif score <= 15:
            self.LATCHED_INTERESTING = False
            self.LATCHED_NOT_INTERESTING = False
            if self.interesting.value > 1:
                self.interesting = Interesting.WATCHLIST
            elif score > 12: self.interesting = Interesting.WATCHLIST
        elif score == 30:
            self.interesting = Interesting.VERY_INTERESTING
            self.LATCHED_INTERESTING = True
            self.LATCHED_NOT_INTERESTING = False
        elif score >= 20:
            self.interesting = Interesting.INTERESTING
            self.LATCHED_INTERESTING = True
            self.LATCHED_NOT_INTERESTING = False
            
        if self.interesting.value > 0:
            return True
        else:
            return False
            
        
        
        
        

        # Neanderthal decision tree for determining boolean interesting-ness of a plane based on dist_nm, altitude, emergency status, and speed_kts. Will be replaced with more sophisticated algorithm in future.
        if self.distance_available:
            if self.dist_nm <= 5:
                return True
            elif self.dist_nm <= 15 and isinstance(self.alt_ft, (int, float)) and self.alt_ft < 15000:# and is_closing
                return True
            elif self.emergency != "unknown" and self.emergency != "none" and self.emergency is not None:
                return True
            elif isinstance(self.speed_kts, (int, float)):
                if self.speed_kts < 200 and self.dist_nm < 8 and self.is_closing:
                    return True
                elif self.speed_kts > 600 and self.is_closing:
                    return True
            
        return False

    

    def update_relational_info(self):
        """Sets relational information about the plane (dist_nm, bearing, angle on bow, etc.) if available. If not available, sets relational_info_available to False."""
        self.dist_nm = distance_nm(home_lat, home_lon, self.lat, self.lon)
        self.bearing_to_plane = get_bearing(home_lat, home_lon, self.lat, self.lon)
        self.recip_bearing = (self.bearing_to_plane + 180) % 360

        if self.relational_info_available:
            self.relative_bearing = (self.recip_bearing - self.track) % 360
            self.angle_on_bow = min(self.relative_bearing, 360 - self.relative_bearing)
            self.is_closing = self.angle_on_bow < 90
                # self.closest_point_of_approach = self.closest_point_of_approach(home_lat, home_lon)


    # def get_rate_of_climb(self):
        # Use combo of ADS-B vertical rate output and recent altitude history to determine whether plane is climbing, descending, or level and at what rate (ft/min)

    # def closest_point_of_approach(self, targ_lat, targ_lon):
        # Find closest point of approach; Return distance, time to CPA, and bearing of of CPA


    # def potentially_interesting(self):


    # def flight_path_analysis(self):
        # Only run if distance_available and relational_info_available are True and plane is 'interesting'
        # Check plane's track, altitude, ground speed, coordinates, and recent history of those values to determine if it might be taking off or landing (very low alt but ascending + low speed but increasing, or descending from cruising alt + slowing down)
        # If flight number available, check if coordinates + track + altitude correlate with origin/destination locations
        # Check plane's coordinates and track to determine whether it might be heading toward preset locations (August, Charlotte, Atlanta, CAE, etc.)
        


    # def decode_flight_number(self):
        # Check flight number to determine whether it is a commercial flight or not (if it is, check flight number against known flights to determine origin/destination)


class Interesting(Enum):
    IGNORE = -1
    NOT_INTERESTING = 0
    WATCHLIST = 1
    INTERESTING = 2
    VERY_INTERESTING = 3

