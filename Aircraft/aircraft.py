from position import distance_nm, get_bearing, get_CPA, load_home_pos, estimate_new_position
from enum import Enum
from math import isfinite

############################################################################
# TODO:
    # -calculate value deltas
    # -assess whether flight number is likely commercial airline number
############################################################################

home_lat, home_lon = load_home_pos()
time_between_cycles = 1.0  # seconds between each cycle of the main loop in adsb_reader.py, used for estimating missing data/position extrapolation

class Aircraft():
    def __init__(self, plane_data):
        self.hex_code = plane_data.get("hex", "unknown")
        self.LATCHED_NOT_INTERESTING = False
        self.LATCHED_INTERESTING = False
        self.stop_tracking_cycles = 0
        self.stop_tracking_update_threshold = 5
        self.interesting = Interesting.NOT_INTERESTING
        self.score = 0.0
        self.debug_score = {
            'proximity score': 0.0,
            'altitude score': 0.0,
            'closing prox. score': 0.0,
            'closing time score': 0.0
        }
        
        self.age = 0
        self.data_age = {'alt_baro': 0, 'gs': 0, 'track': 0, 'emergency': 0, 'lat': 0, 'lon': 0}
        self.missing_data = {'alt_baro': False, 'gs': False, 'track': False, 'emergency': False, 'lat': False, 'lon': False}
        self.based_on_estimates = {'lat': {'is_estimated': False, 'last_known': None, 'confidence': 0.0}, 'lon': {'is_estimated': False, 'last_known': None, 'confidence': 0.0}, 'dist_nm': {'is_estimated': False, 'last_known': None, 'confidence': 0.0}, 'alt_ft': {'is_estimated': False, 'last_known': None, 'confidence': 0.0}, 'track': {'is_estimated': False, 'last_known': None, 'confidence': 0.0}}
        self.delta = {'alt_ft': 0, 'speed_kts': 0, 'track': 0, 'dist_nm': 0, 'bearing_to_plane': 0, 'angle_on_bow': 0, 'relative_bearing': 0}

        self.flight = None
        self.alt_ft = None
        self.alt_terrain = None
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
        self.CPA = {'time_hr': None, 'dist_nm': None, 'bearing': None}
       
        self.buffer_grace = 0
        self.missing_from_receiver = 0
    
        self.update(plane_data, persistent=False)


    ################## Getter Methods #######################

    def update(self, plane_data, persistent=True):
        """
        Main update method. Calls all individual update methods as required.
        Refresh receiver values even when interest has reached STOP_TRACKING.
        """

        self.age += 1
        if persistent: self.old_plane = self.plane
        self.plane = plane_data

        if self.interesting == Interesting.STOP_TRACKING:
            self.stop_tracking_cycles += 1

        self.update_adsb_values(persistent)
        if self.interesting == Interesting.STOP_TRACKING and self.stop_tracking_cycles < 5: return
        self.update_calculated_values(persistent)
        self.update_relational_info(persistent)

        self.interesting = self.update_interesting(persistent)
        
        
    def update_adsb_values(self, persistent=True):
        # Update raw values from ADS-B/receiver
        if self.flight is None:
            # If flight number is not already set, try to get it from plane data. If it is already set, don't update it (to avoid overwriting a previously set flight number with None if the receiver doesn't send it in this cycle)
            self.flight = self.plane.get("flight")
            self.flight = self.flight.strip() if isinstance(self.flight, str) else None

        self.alt_ft = self.get_adsb_data("alt_baro", self.alt_ft, persistent=persistent)
        self.speed_kts = self.get_adsb_data("gs", self.speed_kts, persistent=persistent)
        self.track = self.get_adsb_data("track", self.track, persistent=persistent)
        self.emergency = self.plane.get("emergency")
        self.lat = self.get_adsb_data("lat", self.lat, persistent=persistent)
        self.lon = self.get_adsb_data("lon", self.lon, persistent=persistent)

        # Set availability flags based on whether the data is available and how old it is (if it's too old, consider it unavailable)
        # Lat and lon have a shorter age threshold because they are more critical for calculated values (distance, bearing, etc.). Stale data for lat and lon
        #   can more readily lead to inaccurate values for any dependent values.
        self.altitude_available = True if self.alt_ft is not None and self.data_age['alt_baro'] < 10 else False
        self.groundspeed_available = True if self.speed_kts is not None and self.data_age['gs'] < 10 else False
        if self.interesting == Interesting.STOP_TRACKING and self.stop_tracking_cycles < 5: return

        self.distance_available = True if self.lat is not None and self.lon is not None and self.data_age['lat'] < 5 and self.data_age['lon'] < 5 else False
        self.relational_info_available = True if self.distance_available and self.track is not None and self.groundspeed_available and self.data_age['track'] < 10 else False

    def update_calculated_values(self, persistent=True):
        """Updates calculated values based on ADS-B data (distance, bearing, angle on bow, etc.) if available. If not available, sets relational_info_available to False."""

        if self.distance_available and self.data_age['lat'] == 0 and self.data_age['lon'] == 0:
            self.based_on_estimates['lat']['is_estimated'], self.based_on_estimates['lon']['is_estimated'], self.based_on_estimates['dist_nm']['is_estimated'] = False, False, False
            self.dist_nm = distance_nm(home_lat, home_lon, self.lat, self.lon)
            self.bearing_to_plane = get_bearing(home_lat, home_lon, self.lat, self.lon)
            self.recip_bearing = (self.bearing_to_plane + 180) % 360
                # self.based_on_estimates['lat']['last_known'], self.based_on_estimates['lon']['last_known'] = self.lat, self.lon

        elif self.distance_available and persistent and self.groundspeed_available and self.relational_info_available:
                if not self.based_on_estimates['lat']['is_estimated'] and self.data_age['lat'] > 0:
                    self.based_on_estimates['lat']['last_known'] = self.lat
                    self.based_on_estimates['lat']['is_estimated'] = True

                if not self.based_on_estimates['lon']['is_estimated'] and self.data_age['lon'] > 0:
                    self.based_on_estimates['lon']['last_known'] = self.lon
                    self.based_on_estimates['lon']['is_estimated'] = True

                if self.based_on_estimates['lat']['is_estimated'] or self.based_on_estimates['lon']['is_estimated']:
                    self.based_on_estimates['dist_nm']['is_estimated'] = True
                elif not self.based_on_estimates['lat']['is_estimated'] and not self.based_on_estimates['lon']['is_estimated']:
                    self.based_on_estimates['dist_nm']['is_estimated'] = False

                self.lat, self.lon = estimate_new_position(self.lat, self.lon, self.track, self.speed_kts, (self.data_age['lat'] * time_between_cycles))
                self.based_on_estimates['lat']['confidence'] = max((1 - (self.data_age['lat'] / 5)), 0.0)
                self.based_on_estimates['lon']['confidence'] = max((1 - (self.data_age['lon'] / 5)), 0.0)
                self.based_on_estimates['dist_nm']['confidence'] = (self.based_on_estimates['lat']['confidence'] + self.based_on_estimates['lon']['confidence']) / 2
                
                self.dist_nm = distance_nm(home_lat, home_lon, self.lat, self.lon)
                self.bearing_to_plane = get_bearing(home_lat, home_lon, self.lat, self.lon)
                self.recip_bearing = (self.bearing_to_plane + 180) % 360
        else:
            self.distance_available = False
            self.relational_info_available = False

    def update_relational_info(self, persistent=True):
        """Sets relational information about the plane (dist_nm, bearing, angle on bow, etc.) if available. If not available, sets relational_info_available to False."""
        if self.relational_info_available:
            self.relative_bearing = (self.recip_bearing - self.track) % 360
            self.angle_on_bow = min(self.relative_bearing, 360 - self.relative_bearing)
            self.is_closing = self.angle_on_bow < 90
            if self.groundspeed_available: self.CPA['time_hr'], self.CPA['dist_nm'], self.CPA['bearing']= get_CPA(self.bearing_to_plane, self.dist_nm, self.track, self.speed_kts)

    def get_adsb_data(self, field_name, cur_val=None, persistent=True):
        """
        Extract raw data from ADS-B receiver. 
            -If value is not available, return previous value if persistent is True, otherwise return None. 
            -If persistent is True and value is not available, increment data_age and set missing_data flag for that field.
            -If value is available, resets data_age and missing_data flag for that field.

        Should ensure that no numeric value can exist as non-numeric non-None value, thus avoiding most type errors
        """

        field_value = self.plane.get(field_name)
        
        if isinstance(field_value, (int, float)):
            self.missing_data[field_name] = False
            self.data_age[field_name] = 0
            return field_value
        
        elif field_name == 'alt_baro' and field_value == 'ground':
            self.missing_data[field_name] = False
            self.data_age[field_name] = 0
            return 0.0
        
        else:
            self.missing_data[field_name] = True
            self.data_age[field_name] += 1
            if persistent:
                return cur_val

        return None      

    ################ End Getter Methods ###################

    def update_interesting(self, persistent=True):
        # Takes data from plane and determines how 'interesting' it is.
        
        # Reset scoring values before reaching any early return paths
        data_age_demotion_threshold = 5

        self.score = 0.0
        self.debug_score = {
            'proximity score': 0.0,
            'altitude score': 0.0,
            'closing prox. score': 0.0,
            'closing time score': 0.0
        }
        ### Immediate disqualifiers - if any of these are true, the plane will most likely never become interesting and will be set to STOP_TRACKING or IGNORE (if enough cycles have passed)
        if self.interesting == Interesting.STOP_TRACKING and self.stop_tracking_cycles < 5: return
        
        if not self.altitude_available or not self.groundspeed_available or not self.distance_available or not self.relational_info_available:
            if self.interesting not in [Interesting.IGNORE, Interesting.STOP_TRACKING, Interesting.NOT_INTERESTING]:
                if self.data_age['alt_baro'] >= data_age_demotion_threshold or self.data_age['track'] >= data_age_demotion_threshold or self.data_age['lat'] >= data_age_demotion_threshold or self.data_age['lon'] >= data_age_demotion_threshold or self.data_age['gs'] >= data_age_demotion_threshold:
                    return Interesting.WATCHLIST
                return self.interesting
            else:
                return self.interesting
        if (self.CPA['time_hr'] is not None and self.CPA['time_hr'] < 0) and (self.CPA['dist_nm'] is not None and self.CPA['dist_nm'] > 8) and not self.interesting == Interesting.IGNORE:
            return Interesting.IGNORE

        flight_available = 2.5 if bool(self.flight) else -5.0
        proximity_score = max((20 - self.dist_nm), 0.0) * 0.4 if self.distance_available else -5.0
        altitude_score = max((18000-self.alt_ft)/500, 0.0) * 0.3 if self.altitude_available else -2.0
        closing_proximity_score = max((10 - self.CPA['dist_nm'])*1.75, -10.0) if self.CPA['dist_nm'] is not None and self.is_closing else -10.0
        if (
            self.is_closing and
            self.CPA['time_hr'] is not None and
            self.CPA['time_hr'] > 0 and
            self.CPA['dist_nm'] is not None and
            self.CPA['dist_nm'] <= 8
        ):
            closing_time_score = max((15 - (self.CPA['time_hr'] * 60))/1.8, -2.5)
        elif self.CPA['time_hr'] <= -2.5:
            closing_time_score = -15
        else:
            closing_time_score = 0

        self.score = (
            flight_available +
            proximity_score +
            altitude_score +
            closing_proximity_score +
            closing_time_score
        )

        self.debug_score = {
            'proximity score': proximity_score,
            'altitude score': altitude_score,
            'closing prox. score': closing_proximity_score,
            'closing time score': closing_time_score,
            'flight avail.': flight_available
        }
        
        # Apply visibility limits before any score or airport-pattern promotion.
        if self.alt_ft <= 0 or self.speed_kts <= 0:
            return Interesting.IGNORE

        low_alt = (self.alt_ft <= 10000)
        within_viewing_range = (self.dist_nm <= 8)
        visible_soon = (self.dist_nm <= 15 and self.is_closing and
                        self.CPA['time_hr'] is not None and 0 < self.CPA['time_hr'] <= 5 / 60 and
                        self.CPA['dist_nm'] is not None and self.CPA['dist_nm'] <= 8)
        
        if not low_alt or not (within_viewing_range or visible_soon):
            return Interesting.WATCHLIST if self.score >= 8 else Interesting.IGNORE

        # Rates are optional receiver values; do not infer climb/descent from a callsign.
        vertical_rate = self.plane.get('baro_rate')
        if not isinstance(vertical_rate, (int, float)) or not isfinite(vertical_rate):
            vertical_rate = self.plane.get('geom_rate')

        rate_available = isinstance(vertical_rate, (int, float)) and isfinite(vertical_rate)
        climbing = rate_available and vertical_rate >= 300
        descending = rate_available and vertical_rate <= -300
        viewing_speed = (180 <= self.speed_kts <= 300)
        airport_movement = within_viewing_range and (
            (climbing and 160 < self.speed_kts <= 300) or
            (descending and 120 <= self.speed_kts <= 300)
        )

        if airport_movement:
            return Interesting.VERY_INTERESTING
        if viewing_speed:
            return Interesting.VERY_INTERESTING if self.score >= 30 else Interesting.INTERESTING

        # Slow final approaches remain candidates when vertical rate is unavailable.
        possible_airliner_land = (within_viewing_range and self.alt_ft <= 7500 and
                                  120 <= self.speed_kts < 180 and not rate_available and bool(self.flight))
        
        very_near_low = (self.dist_nm <= 2.5 and self.alt_ft <= 7500 and 60 < self.speed_kts < 180)
        if possible_airliner_land or very_near_low:
            return Interesting.INTERESTING
        
        return Interesting.WATCHLIST

    def stop_tracking(self):
        self.interesting = Interesting.STOP_TRACKING
        self.stop_tracking_cycles = 0
        self.distance_available = False
        self.relational_info_available = False


class Interesting(Enum):
    STOP_TRACKING = -2
    IGNORE = -1
    NOT_INTERESTING = 0
    WATCHLIST = 1
    INTERESTING = 2
    VERY_INTERESTING = 3
