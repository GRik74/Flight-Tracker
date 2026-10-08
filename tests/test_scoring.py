"""Compare scoring against historical versions and independent viewing criteria."""

import json
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from Aircraft.aircraft import Aircraft, Interesting, home_lat, home_lon
from scoring_baselines import pre_modifier_interest, refactor_interest


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "Sample Files"
INTERESTING = {Interesting.INTERESTING, Interesting.VERY_INTERESTING}


def classify(rows, scoring=None):
    if scoring is None:
        return [Aircraft(row) for row in rows]
    with patch.object(Aircraft, "update_interesting", scoring):
        return [Aircraft(row) for row in rows]


def viewing_candidate(plane):
    """A viewing proxy, independent of scores, callsigns, and assigned states.

    Prefer nearby aircraft below 10,000 ft moving above 150 kt, or an imminent
    close pass below 30,000 ft. Also include very nearby low, slow aircraft.
    This describes likely viewing interest; the snapshots have no human labels.
    """
    if not (plane.altitude_available and plane.groundspeed_available and
            plane.distance_available and plane.relational_info_available):
        return False
    nearby_low = plane.alt_ft <= 10000 and plane.dist_nm <= 10 and plane.speed_kts > 150
    imminent_pass = (plane.alt_ft < 30000 and plane.dist_nm <= 4 and plane.speed_kts > 150 and
                     plane.CPA['dist_nm'] is not None and plane.CPA['dist_nm'] <= 2 and
                     plane.CPA['time_hr'] is not None and 0 <= plane.CPA['time_hr'] <= 3 / 60)
    very_near_low = plane.alt_ft <= 7500 and plane.dist_nm <= 4
    return nearby_low or imminent_pass or very_near_low


def synthetic_plane(distance=6, altitude=1000, speed=200, track=0, flight="TEST123"):
    # Place the aircraft due north using the same Earth radius as position.py.
    return {"hex": "test123", "flight": flight, "alt_baro": altitude,
            "gs": speed, "track": track, "emergency": "none",
            "lat": home_lat + math.degrees(distance / 3440.065), "lon": home_lon}


class SampleScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = {
            f"sample{number}.json": json.loads((SAMPLE_DIR / f"sample{number}.json").read_text())["aircraft"]
            for number in range(5, 10)
        }
        cls.comparisons = {
            name: (classify(rows), classify(rows, pre_modifier_interest), classify(rows, refactor_interest))
            for name, rows in cls.samples.items()
        }

    def test_all_new_sample_records_produce_valid_states_and_scores(self):
        self.assertGreaterEqual(sum(map(len, self.samples.values())), 500)
        self.assertGreaterEqual(sum(len(rows) > 100 for rows in self.samples.values()), 3)
        for name, (current, _, _) in self.comparisons.items():
            for plane in current:
                with self.subTest(sample=name, hex_code=plane.hex_code):
                    self.assertIsInstance(plane.interesting, Interesting)
                    self.assertTrue(math.isfinite(plane.score))
                    self.assertEqual(len(plane.debug_score), 4)
                    self.assertTrue(all(math.isfinite(score) for score in plane.debug_score.values()))

    def test_candidate_coverage_improves_over_original_refactor(self):
        candidates = original_hits = current_hits = 0
        for current, _, original in self.comparisons.values():
            for plane, old in zip(current, original):
                if viewing_candidate(plane):
                    candidates += 1
                    current_hits += plane.interesting in INTERESTING
                    original_hits += old.interesting in INTERESTING
        self.assertGreaterEqual(candidates, 3)
        self.assertGreater(current_hits, original_hits)
        self.assertEqual(current_hits, candidates)

    def test_latest_modifiers_preserve_candidate_coverage_in_every_sample(self):
        for name, (current, previous, _) in self.comparisons.items():
            with self.subTest(sample=name):
                current_hits = sum(viewing_candidate(p) and p.interesting in INTERESTING for p in current)
                previous_hits = sum(viewing_candidate(p) and p.interesting in INTERESTING for p in previous)
                self.assertGreaterEqual(current_hits, previous_hits)

    def test_latest_modifiers_improve_fraction_of_selected_aircraft_meeting_viewing_criteria(self):
        current_selected = current_hits = previous_selected = previous_hits = 0
        for current, previous, _ in self.comparisons.values():
            for plane, old in zip(current, previous):
                if plane.interesting in INTERESTING:
                    current_selected += 1
                    current_hits += viewing_candidate(plane)
                if old.interesting in INTERESTING:
                    previous_selected += 1
                    previous_hits += viewing_candidate(old)
        self.assertGreater(current_selected, 0)
        self.assertGreater(previous_selected, 0)
        self.assertGreater(current_hits / current_selected, previous_hits / previous_selected)
        self.assertEqual(current_hits, current_selected)


class SyntheticScoringTests(unittest.TestCase):
    def test_nearby_low_departures_are_promoted_from_watchlist(self):
        # Use real positions/CPA calculations, rather than mocking assigned scores.
        for distance in (2, 4, 6):
            for altitude in (1000, 2000):
                for speed in (180, 220, 280):
                    with self.subTest(distance=distance, altitude=altitude, speed=speed):
                        row = synthetic_plane(distance, altitude, speed)
                        current = Aircraft(row)
                        previous = classify([row], pre_modifier_interest)[0]
                        self.assertGreaterEqual(current.score, 10)
                        self.assertLess(current.score, 20)
                        self.assertEqual(previous.interesting, Interesting.WATCHLIST)
                        self.assertEqual(current.interesting, Interesting.INTERESTING)

    def test_distant_or_high_cruise_is_demoted_from_interesting(self):
        for row in (synthetic_plane(30, 20000, 500, 180),
                    synthetic_plane(10, 33000, 500, 180)):
            with self.subTest(row=row):
                current = Aircraft(row)
                previous = classify([row], pre_modifier_interest)[0]
                self.assertIn(previous.interesting, INTERESTING)
                self.assertEqual(current.interesting, Interesting.WATCHLIST)

    def test_missing_initial_data_stays_uninteresting(self):
        for field in ('alt_baro', 'gs', 'track', 'lat', 'lon'):
            with self.subTest(field=field):
                row = synthetic_plane()
                del row[field]
                plane = Aircraft(row)
                self.assertEqual(plane.interesting, Interesting.NOT_INTERESTING)
                self.assertEqual(plane.score, 0)
                self.assertTrue(all(score == 0 for score in plane.debug_score.values()))

    def test_aged_positions_demote_interest_and_clear_scores(self):
        plane = Aircraft(synthetic_plane(track=180))
        self.assertIn(plane.interesting, INTERESTING)
        row = synthetic_plane(track=180)
        del row['lat'], row['lon']
        for _ in range(5):
            plane.update(row)
        self.assertEqual(plane.interesting, Interesting.WATCHLIST)
        self.assertFalse(plane.distance_available)
        self.assertEqual(plane.score, 0)
        self.assertTrue(all(score == 0 for score in plane.debug_score.values()))

    @unittest.expectedFailure
    def test_landing_candidate_in_middle_score_band_is_promoted(self):
        # Known issue at aircraft.py:256: climb and landing conditions cannot
        # both hold, so the low-speed guard blocks the landing promotion.
        row = synthetic_plane(distance=6, altitude=2000, speed=140)
        plane = Aircraft(row)
        self.assertGreaterEqual(plane.score, 10)
        self.assertLess(plane.score, 20)
        self.assertEqual(plane.interesting, Interesting.INTERESTING)

    @unittest.expectedFailure
    def test_previously_interesting_aircraft_handles_nonpersistent_missing_data(self):
        # Known issue at aircraft.py:197-202: unavailable data younger than
        # five cycles falls through; numeric modifiers then compare None.
        plane = Aircraft(synthetic_plane(track=180))
        self.assertIn(plane.interesting, INTERESTING)
        plane.update({"hex": "test123"}, persistent=False)
        self.assertIsInstance(plane.interesting, Interesting)

    @unittest.expectedFailure
    def test_high_altitude_limit_also_applies_above_thirty_points(self):
        # The >=30 branch bypasses the high-altitude limit used below 30.
        plane = Aircraft(synthetic_plane(distance=2, altitude=33000, speed=500, track=180))
        self.assertGreaterEqual(plane.score, 30)
        self.assertEqual(plane.interesting, Interesting.WATCHLIST)

    @unittest.expectedFailure
    def test_distance_limit_also_applies_above_thirty_points(self):
        # A low aircraft 30 nm away can score >=30 and bypass not_close.
        plane = Aircraft(synthetic_plane(distance=30, altitude=1000, speed=500, track=180))
        self.assertGreaterEqual(plane.score, 30)
        self.assertEqual(plane.interesting, Interesting.WATCHLIST)


if __name__ == "__main__":
    unittest.main()
