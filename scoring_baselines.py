"""Frozen scoring methods for first-snapshot comparisons.

These references retain the historical formulas and thresholds. Tests patch only
Aircraft.update_interesting, so all versions use the same receiver parsing and
position calculations. No Git checkout or network access is needed to run them.
"""

from Aircraft.aircraft import Interesting


# Aircraft.update_interesting at 0b87ae4
def refactor_interest(self, persistent=True):

    if self.interesting == Interesting.STOP_TRACKING: return self.interesting

    if not self.altitude_available or not self.groundspeed_available or not self.distance_available or not self.relational_info_available:
        if self.interesting == Interesting.IGNORE: return Interesting.IGNORE
        if self.interesting == Interesting.NOT_INTERESTING:
            self.LATCHED_NOT_INTERESTING = True
            return Interesting.NOT_INTERESTING
        if self.LATCHED_INTERESTING: self.LATCHED_INTERESTING = False
        return Interesting.NOT_INTERESTING
    if (self.CPA['time_hr'] is not None and self.CPA['time_hr'] < 0) and (self.CPA['dist_nm'] is not None and self.CPA['dist_nm'] > 8) and not self.interesting == Interesting.IGNORE:
        return Interesting.IGNORE

    dist_factor = max((20.0 - self.dist_nm), 0.0) * 0.5 if self.distance_available else 0.0
    alt_factor = max((25000 - self.alt_ft)/2000, 0.0) * 0.2 if self.altitude_available else 0.0
    aob_factor = ((90 - self.angle_on_bow)/9) * 0.3 if self.relational_info_available else 0.0

    pos_factors = (dist_factor + alt_factor + aob_factor) / 3

    speed_factor = max((600 - self.speed_kts)/60, 0.0) * 0.1 if self.groundspeed_available else 0.0 # Need to remove or rework - doesn't make senseto favor faster aircraft just because they're fast
    if self.CPA['time_hr'] is not None and self.CPA['time_hr'] > 0 and self.CPA['dist_nm'] is not None and self.CPA['dist_nm'] > 0:
        cpa_mins = self.CPA['time_hr'] * 60
        cpa_time_factor = max((10.0 - cpa_mins), 0.0) * 0.3
        cpa_dist_factor = max((10.0 - self.CPA['dist_nm']), 0.0)**1.5 * 0.6
    else:
        cpa_time_factor = 0.0
        cpa_dist_factor = 0.0

    behavioral_factors = (speed_factor + cpa_time_factor + cpa_dist_factor) / 3

    emergency_bonus = ((dist_factor/10) + 1) if self.emergency != "unknown" and self.emergency != "none" and self.emergency is not None else 0.0
    neg_cpa_time_bonus = 0.0
    if self.CPA['time_hr'] is not None and self.CPA['time_hr'] < 0:
        neg_cpa_time_bonus = 1.0 if self.CPA['dist_nm'] < 3 else -1.0

    bonus_factors = (emergency_bonus + neg_cpa_time_bonus)

    very_low_alt_mult = (1 + ((5000 - self.alt_ft) * 0.00002))**(max(cpa_dist_factor / 10, 1.0)) if self.alt_ft < 5000 else 1.0

    base_score = (pos_factors + behavioral_factors + bonus_factors)
    self.score = min((base_score * very_low_alt_mult), 30)
    self.debug_score = base_score * very_low_alt_mult

    if self.score < 5:
        self.LATCHED_NOT_INTERESTING = True
        self.LATCHED_INTERESTING = False
        return Interesting.IGNORE
    elif self.score < 10:
        self.LATCHED_NOT_INTERESTING = True
        self.LATCHED_INTERESTING = False
        return Interesting.NOT_INTERESTING
    elif self.score <= 15:
        self.LATCHED_INTERESTING = False
        self.LATCHED_NOT_INTERESTING = False
        return Interesting.WATCHLIST

    elif self.score == 30:
        self.LATCHED_INTERESTING = True
        self.LATCHED_NOT_INTERESTING = False
        return Interesting.VERY_INTERESTING
    elif self.score >= 20:
        self.LATCHED_INTERESTING = True
        self.LATCHED_NOT_INTERESTING = False
        return Interesting.INTERESTING

    elif self.score > 15:
        self.LATCHED_INTERESTING = False
        self.LATCHED_NOT_INTERESTING = False
        return Interesting.WATCHLIST

    else:
        return Interesting.WATCHLIST

# Aircraft.update_interesting at 942aab3
def pre_modifier_interest(self, persistent=True):

    self.score = 0.0
    self.debug_score = {
        'proximity score': 0.0,
        'altitude score': 0.0,
        'closing prox. score': 0.0,
        'closing time score': 0.0
    }
    if self.interesting == Interesting.STOP_TRACKING: return self.interesting

    if not self.altitude_available or not self.groundspeed_available or not self.distance_available or not self.relational_info_available:
        if self.interesting == Interesting.IGNORE: return Interesting.IGNORE
        if self.interesting == Interesting.NOT_INTERESTING:
            self.LATCHED_NOT_INTERESTING = True
            return Interesting.NOT_INTERESTING
        if self.LATCHED_INTERESTING: self.LATCHED_INTERESTING = False
        return Interesting.NOT_INTERESTING
    if (self.CPA['time_hr'] is not None and self.CPA['time_hr'] < 0) and (self.CPA['dist_nm'] is not None and self.CPA['dist_nm'] > 8) and not self.interesting == Interesting.IGNORE:
        return Interesting.IGNORE

    proximity_score = max((20 - self.dist_nm), 0.0) * 0.4 if self.distance_available else -5.0
    altitude_score = max((18000-self.alt_ft)/500, 0.0) * 0.3 if self.altitude_available else -2.0
    closing_proximity_score = max((10 - self.CPA['dist_nm']), 0.0) if self.CPA['dist_nm'] is not None and self.is_closing else -2.5
    closing_time_score = max((15 - (self.CPA['time_hr'] * 60))*1.1, 0.0) if self.CPA['time_hr'] is not None and self.is_closing else -2.5

    self.score = (
        proximity_score +
        altitude_score +
        closing_proximity_score +
        closing_time_score
    )

    self.debug_score = {
        'proximity score': proximity_score,
        'altitude score': altitude_score,
        'closing prox. score': closing_proximity_score,
        'closing time score': closing_time_score
    }

    if self.score < 5:
        return Interesting.IGNORE

    elif self.score < 10:
        return Interesting.NOT_INTERESTING

    elif self.score < 20:
        return Interesting.WATCHLIST

    elif self.score < 30:
        return Interesting.INTERESTING

    else:
        return Interesting.VERY_INTERESTING
