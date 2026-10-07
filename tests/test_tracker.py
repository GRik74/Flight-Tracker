import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import main
from Aircraft.aircraft import Aircraft, Interesting, home_lat, home_lon
from Aircraft.tracker import AircraftTracker, interest_grace, missing_grace


def plane_data(hex_code="abc123", offset=0.01):
    return {"hex": hex_code, "lat": home_lat + offset, "lon": home_lon,
            "alt_baro": 1000, "gs": 200, "track": 180, "emergency": "none"}


class AircraftTrackerTests(unittest.TestCase):
    def setUp(self):
        self.debug = patch("Aircraft.tracker.DEBUG", False)
        self.debug.start()
        self.addCleanup(self.debug.stop)
        self.tracker = AircraftTracker()

    def test_new_aircraft_inserted_and_reused(self):
        self.tracker.update_tracked_planes([plane_data(), {}, {"hex": ""}])
        plane = self.tracker.tracked_planes["abc123"]
        self.assertEqual(self.tracker.current_planes, [plane])
        self.assertEqual(self.tracker.active, [plane])
        self.assertEqual(self.tracker.current_codes, {"abc123"})
        self.tracker.update_tracked_planes([plane_data(offset=0.02)])
        self.assertIs(self.tracker.tracked_planes["abc123"], plane)
        self.assertEqual(plane.age, 2)
        self.assertEqual(plane.lat, home_lat + 0.02)

    def test_initial_watchlist_does_not_consume_grace(self):
        with patch.object(Aircraft, "update_interesting", return_value=Interesting.WATCHLIST):
            self.tracker.update_tracked_planes([plane_data()])
        self.assertEqual(self.tracker.tracked_planes["abc123"].buffer_grace, 0)

    def test_interest_recovery_at_threshold_uses_current_state(self):
        with patch.object(Aircraft, "update_interesting", return_value=Interesting.NOT_INTERESTING):
            self.tracker.update_tracked_planes([plane_data()])
        plane = self.tracker.tracked_planes["abc123"]
        for state in (Interesting.WATCHLIST, Interesting.INTERESTING, Interesting.VERY_INTERESTING):
            plane.interesting = Interesting.NOT_INTERESTING
            plane.buffer_grace = interest_grace
            with patch.object(Aircraft, "update_interesting", return_value=state):
                self.tracker.update_tracked_planes([plane_data()])
            self.assertEqual(plane.interesting, state)
            self.assertEqual(plane.buffer_grace, 0)

    def test_interest_loss_consumes_grace_immediately(self):
        with patch.object(Aircraft, "update_interesting", return_value=Interesting.INTERESTING):
            self.tracker.update_tracked_planes([plane_data()])
        with patch.object(Aircraft, "update_interesting", return_value=Interesting.NOT_INTERESTING):
            self.tracker.update_tracked_planes([plane_data()])
        plane = self.tracker.tracked_planes["abc123"]
        self.assertEqual(plane.interesting, Interesting.NOT_INTERESTING)
        self.assertEqual(plane.buffer_grace, 1)

    def test_stop_tracking_after_interest_grace_and_refresh_raw_values(self):
        # Positionless aircraft exhaust interest grace without mocked scoring.
        data = {"hex": "abc123"}
        for _ in range(interest_grace):
            self.tracker.update_tracked_planes([data])
        plane = self.tracker.tracked_planes["abc123"]
        self.assertEqual(plane.buffer_grace, interest_grace)
        self.assertEqual(plane.interesting, Interesting.NOT_INTERESTING)
        self.assertEqual(self.tracker.active, [plane])
        self.tracker.update_tracked_planes([data])
        self.assertEqual(plane.interesting, Interesting.STOP_TRACKING)
        self.assertEqual(self.tracker.current_planes, [plane])
        self.assertEqual(self.tracker.active, [])
        self.tracker.update_tracked_planes([plane_data()])
        self.tracker.update_tracked_planes([plane_data(offset=0.02)])
        self.assertEqual(plane.lat, home_lat + 0.02)
        self.assertEqual(plane.lon, home_lon)
        self.assertEqual(plane.alt_ft, 1000)
        self.assertEqual(plane.speed_kts, 200)
        self.assertEqual(plane.data_age['lat'], 0)
        self.assertEqual(plane.age, interest_grace + 3)
        self.assertIsNone(plane.dist_nm)
        self.assertFalse(plane.distance_available)
        self.assertFalse(plane.relational_info_available)
        self.assertEqual(plane.interesting, Interesting.STOP_TRACKING)
        self.assertEqual(plane.buffer_grace, interest_grace)
        self.assertEqual(plane.missing_from_receiver, 0)
        self.assertEqual(self.tracker.active, [])

    def test_stop_tracking_suppresses_previously_positioned_aircraft(self):
        data = plane_data(offset=1.0)
        data.update(alt_baro=35000, track=0)
        for _ in range(interest_grace):
            self.tracker.update_tracked_planes([data])
        plane = self.tracker.tracked_planes["abc123"]
        self.assertEqual(plane.interesting, Interesting.IGNORE)
        self.assertTrue(plane.distance_available)
        old_distance = plane.dist_nm
        self.tracker.update_tracked_planes([data])
        self.assertEqual(plane.interesting, Interesting.STOP_TRACKING)
        self.assertFalse(plane.distance_available)
        self.assertFalse(plane.relational_info_available)
        self.tracker.update_tracked_planes([plane_data()])
        self.assertEqual(plane.lat, home_lat + 0.01)
        self.assertEqual(plane.dist_nm, old_distance)
        self.assertFalse(plane.distance_available)
        self.assertFalse(plane.relational_info_available)
        self.assertEqual(self.tracker.current_planes, [plane])
        self.assertEqual(self.tracker.active, [])

    def test_missing_receiver_has_independent_grace_and_resets(self):
        self.tracker.update_tracked_planes([{"hex": "abc123"}])
        plane = self.tracker.tracked_planes["abc123"]
        plane.buffer_grace = interest_grace
        self.tracker.update_tracked_planes([])
        self.assertIs(self.tracker.tracked_planes["abc123"], plane)
        self.assertEqual(plane.missing_from_receiver, 1)
        self.assertEqual(plane.buffer_grace, interest_grace)
        self.assertEqual(self.tracker.current_planes, [])
        self.assertEqual(self.tracker.active, [])
        self.assertEqual(self.tracker.current_codes, set())
        self.tracker.update_tracked_planes([plane_data()])
        self.assertEqual(plane.missing_from_receiver, 0)
        for _ in range(missing_grace):
            self.tracker.update_tracked_planes([])
        self.assertIs(self.tracker.tracked_planes["abc123"], plane)
        self.assertEqual(plane.missing_from_receiver, missing_grace)
        self.tracker.update_tracked_planes([])
        self.assertNotIn("abc123", self.tracker.tracked_planes)
        self.tracker.update_tracked_planes([plane_data()])
        self.assertIsNot(self.tracker.tracked_planes["abc123"], plane)

    def test_heard_plane_with_expired_position_is_unavailable(self):
        self.tracker.update_tracked_planes([plane_data()])
        plane = self.tracker.tracked_planes["abc123"]
        for _ in range(5):
            self.tracker.update_tracked_planes([{"hex": "abc123"}])
        self.assertEqual(self.tracker.current_planes, [plane])
        self.assertFalse(plane.distance_available)
        self.assertIsNotNone(plane.dist_nm)
        self.assertEqual(plane.missing_from_receiver, 0)

    def run_main(self, snapshots, interest=Interesting.IGNORE):
        with patch.object(main, "AircraftTracker", return_value=self.tracker), \
                patch.object(main, "load_aircraft", side_effect=snapshots), \
                patch.object(main, "show_planes") as show, \
                patch.object(main, "DEBUG", False), \
                patch("builtins.input", side_effect=["y"] * (len(snapshots) - 1) + ["n"]), \
                patch.object(Aircraft, "update_interesting", return_value=interest), \
                redirect_stdout(StringIO()):
            main.main()
        return [[plane.hex_code for plane in call.args[0]] for call in show.call_args_list]

    def test_main_closest_excludes_retained_and_positionless_aircraft(self):
        shown = self.run_main([
            [plane_data("old", 0.01)],
            [plane_data("current", 0.02), {"hex": "positionless"}],
            [{"hex": "positionless"}],
            [],
        ])
        self.assertEqual(shown, [["old"], ["current"], [], []])
        self.assertEqual(set(self.tracker.tracked_planes), {"old", "current", "positionless"})

    def test_main_does_not_display_retained_interesting_aircraft(self):
        shown = self.run_main([[plane_data()], []], interest=Interesting.INTERESTING)
        self.assertEqual(shown, [["abc123"], []])

    def test_main_closest_excludes_expired_positions(self):
        shown = self.run_main([[plane_data()]] + [[{"hex": "abc123"}]] * 5)
        self.assertEqual(shown[-1], [])
        self.assertIn("abc123", self.tracker.tracked_planes)

    def test_main_closest_excludes_stopped_aircraft(self):
        shown = self.run_main(
            [[plane_data("stopped")]] * (interest_grace + 1) +
            [[plane_data("stopped"), plane_data("active", 0.02)]]
        )
        self.assertEqual(shown[:interest_grace], [["stopped"]] * interest_grace)
        self.assertEqual(shown[-2:], [[], ["active"]])
        self.assertEqual(set(self.tracker.tracked_planes), {"stopped", "active"})
        self.assertEqual([plane.hex_code for plane in self.tracker.current_planes], ["stopped", "active"])
        self.assertEqual([plane.hex_code for plane in self.tracker.active], ["active"])


if __name__ == "__main__":
    unittest.main()
