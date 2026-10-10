"""Compare scoring against historical versions and independent viewing criteria."""

import json
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from Aircraft.aircraft import Aircraft, Interesting, home_lat, home_lon
from Aircraft.tracker import AircraftTracker
from scoring_baselines import pre_modifier_interest, refactor_interest


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "Sample Files"
INTERESTING = {Interesting.INTERESTING, Interesting.VERY_INTERESTING}


def classify(rows, scoring=None):
    if scoring is None:
        return [Aircraft(row) for row in rows]
    with patch.object(Aircraft, "update_interesting", scoring):
        return [Aircraft(row) for row in rows]


def viewing_candidate(plane):
    """The user's visibility criteria, independent of scores and assigned states.

    Generally <=10,000 ft, <=8 nm, and 180–300 kt. Include imminent nearby
    passes and slower descending approaches. Snapshots have no human labels.
    """
    if not (plane.altitude_available and plane.groundspeed_available and
            plane.distance_available and plane.relational_info_available):
        return False
    if not (0 < plane.alt_ft <= 10000):
        return False
    nearby_low = plane.dist_nm <= 8 and 180 <= plane.speed_kts <= 300
    imminent_pass = (plane.dist_nm <= 15 and 180 <= plane.speed_kts <= 300 and plane.is_closing and
                     plane.CPA['dist_nm'] is not None and plane.CPA['dist_nm'] <= 8 and
                     plane.CPA['time_hr'] is not None and 0 < plane.CPA['time_hr'] <= 5 / 60)
    rate = plane.plane.get('baro_rate', plane.plane.get('geom_rate'))
    airport_movement = (plane.dist_nm <= 8 and isinstance(rate, (int, float)) and
                        ((rate >= 300 and 160 < plane.speed_kts <= 300) or
                         (rate <= -300 and 120 <= plane.speed_kts <= 300)))
    return nearby_low or imminent_pass or airport_movement


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
        self.assertGreaterEqual(candidates, 1)
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

    def test_sample_approaches_and_departures_are_recovered(self):
        for number, expected in (
            (2, {'a6b10c', 'abd7d1'}),
            (4, {'a81832', 'a85568', 'a1c5e0'}),
            (5, {'a16c2c'}),
        ):
            with self.subTest(sample=number):
                rows = json.loads((SAMPLE_DIR / f"sample{number}.json").read_text())["aircraft"]
                current = classify(rows)
                previous = classify(rows, pre_modifier_interest)
                selected = {p.hex_code for p in current if p.interesting in INTERESTING}
                self.assertEqual(selected, expected)
                self.assertTrue(all(p.interesting == Interesting.VERY_INTERESTING
                                    for p in current if p.hex_code in expected))
                previous_hits = sum(p.hex_code in expected and p.interesting in INTERESTING for p in previous)
                self.assertGreater(len(selected), previous_hits)

    def test_tracker_replays_all_samples_without_invalid_states(self):
        with patch('Aircraft.tracker.DEBUG', False):
            tracker = AircraftTracker()
            for path in sorted(SAMPLE_DIR.glob('sample*.json')):
                rows = json.loads(path.read_text())["aircraft"]
                for _ in range(35):
                    tracker.update_tracked_planes(rows)
                    for plane in tracker.current_planes:
                        with self.subTest(sample=path.name, hex_code=plane.hex_code):
                            self.assertIsInstance(plane.interesting, Interesting)
                            self.assertTrue(math.isfinite(plane.score))
                            if plane in tracker.active:
                                self.assertNotEqual(plane.interesting, Interesting.STOP_TRACKING)


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

    def test_landing_candidate_in_middle_score_band_is_promoted(self):
        # A slow approach with missing rate must not be blocked by a climb guard.
        row = synthetic_plane(distance=6, altitude=2000, speed=140)
        plane = Aircraft(row)
        self.assertGreaterEqual(plane.score, 10)
        self.assertLess(plane.score, 20)
        self.assertEqual(plane.interesting, Interesting.INTERESTING)

    def test_previously_interesting_aircraft_handles_nonpersistent_missing_data(self):
        # Missing values must return before numeric modifiers are evaluated.
        plane = Aircraft(synthetic_plane(track=180))
        self.assertIn(plane.interesting, INTERESTING)
        plane.update({"hex": "test123"}, persistent=False)
        self.assertEqual(plane.interesting, Interesting.VERY_INTERESTING)
        self.assertEqual(plane.score, 0)
        for _ in range(4):
            plane.update({"hex": "test123"}, persistent=False)
        self.assertEqual(plane.interesting, Interesting.WATCHLIST)

    def test_high_altitude_limit_also_applies_above_thirty_points(self):
        plane = Aircraft(synthetic_plane(distance=2, altitude=33000, speed=500, track=180))
        self.assertGreaterEqual(plane.score, 30)
        self.assertEqual(plane.interesting, Interesting.WATCHLIST)

    def test_distance_limit_also_applies_above_thirty_points(self):
        plane = Aircraft(synthetic_plane(distance=30, altitude=1000, speed=500, track=180))
        self.assertGreaterEqual(plane.score, 30)
        self.assertEqual(plane.interesting, Interesting.WATCHLIST)

    def test_typical_visible_aircraft_do_not_need_a_callsign_or_high_score(self):
        plane = Aircraft(synthetic_plane(distance=7.9, altitude=10000, speed=200, flight=None))
        self.assertLess(plane.score, 5)
        self.assertEqual(plane.interesting, Interesting.INTERESTING)

    def test_visibility_and_speed_boundaries(self):
        for distance, altitude, speed, expected in (
            (8, 10000, 180, Interesting.INTERESTING),
            (8, 10000, 300, Interesting.INTERESTING),
            (8.01, 10000, 200, Interesting.IGNORE),
            (8, 10001, 200, Interesting.IGNORE),
            (8, 10000, 179, Interesting.WATCHLIST),
            (8, 10000, 301, Interesting.WATCHLIST),
        ):
            with self.subTest(distance=distance, altitude=altitude, speed=speed):
                plane = Aircraft(synthetic_plane(distance, altitude, speed, flight=None))
                # Avoid a floating-point round trip moving an exact 8 nm test
                # just over the boundary in the position calculation.
                plane.dist_nm = distance
                self.assertEqual(plane.update_interesting(), expected)

    def test_climb_and_descent_prioritized_using_reported_rates(self):
        for speed, rate in ((200, 1000), (200, -1000), (140, -700), (175, 700)):
            with self.subTest(speed=speed, rate=rate):
                row = synthetic_plane(speed=speed, flight=None)
                row['baro_rate'] = rate
                self.assertEqual(Aircraft(row).interesting, Interesting.VERY_INTERESTING)

    def test_approach_rate_does_not_depend_on_heading_toward_home(self):
        row = synthetic_plane(speed=140, track=0)
        row['baro_rate'] = -700
        plane = Aircraft(row)
        self.assertFalse(plane.is_closing)
        self.assertEqual(plane.interesting, Interesting.VERY_INTERESTING)

    def test_callsign_alone_does_not_make_level_flight_very_interesting(self):
        row = synthetic_plane()
        row['baro_rate'] = 0
        self.assertEqual(Aircraft(row).interesting, Interesting.INTERESTING)
        row['gs'] = 140
        self.assertEqual(Aircraft(row).interesting, Interesting.WATCHLIST)

    def test_vertical_rate_fallback_and_invalid_values(self):
        for invalid in (None, 'unknown', float('nan'), float('inf')):
            with self.subTest(rate=invalid):
                row = synthetic_plane()
                row.update(baro_rate=invalid, geom_rate=1000)
                self.assertEqual(Aircraft(row).interesting, Interesting.VERY_INTERESTING)
                row['geom_rate'] = invalid
                self.assertEqual(Aircraft(row).interesting, Interesting.INTERESTING)

    def test_inbound_aircraft_can_be_interesting_before_entering_viewing_range(self):
        for distance, speed, expected in (
            (12, 200, Interesting.VERY_INTERESTING),
            (15, 180, Interesting.VERY_INTERESTING),
            (16, 200, Interesting.WATCHLIST),
            (12, 200, Interesting.WATCHLIST),
        ):
            with self.subTest(distance=distance, speed=speed, expected=expected):
                track = 0 if expected == Interesting.WATCHLIST and distance == 12 else 180
                plane = Aircraft(synthetic_plane(distance=distance, speed=speed, track=track))
                self.assertEqual(plane.interesting, expected)

    def test_high_score_does_not_promote_aircraft_outside_preferred_speed_band(self):
        for speed in (100, 350, 500):
            with self.subTest(speed=speed):
                plane = Aircraft(synthetic_plane(distance=6, speed=speed, track=180))
                self.assertGreaterEqual(plane.score, 30)
                self.assertEqual(plane.interesting, Interesting.WATCHLIST)

    def test_grounded_aircraft_are_ignored(self):
        for altitude, speed in (('ground', 200), (0, 200), (1000, 0)):
            with self.subTest(altitude=altitude, speed=speed):
                plane = Aircraft(synthetic_plane(altitude=altitude, speed=speed))
                self.assertEqual(plane.interesting, Interesting.IGNORE)

    def test_partial_missing_fields_cannot_promote_previous_state(self):
        for state in (Interesting.WATCHLIST, Interesting.INTERESTING, Interesting.VERY_INTERESTING):
            for field in ('alt_baro', 'gs', 'track', 'lat', 'lon'):
                with self.subTest(state=state, field=field):
                    plane = Aircraft(synthetic_plane())
                    plane.interesting = state
                    row = synthetic_plane()
                    del row[field]
                    plane.update(row, persistent=False)
                    self.assertEqual(plane.interesting, state)
                    self.assertEqual(plane.score, 0)


if __name__ == "__main__":
    unittest.main()
