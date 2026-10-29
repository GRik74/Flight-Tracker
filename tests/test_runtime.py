"""Runtime edge cases. Expected failures document unfixed application defects.

Remove each expectedFailure decorator when its application fix is authorized.
No receiver, terminal, wall-clock delay, or external service is required.
"""

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import adsb_reader
import main
import output
from Aircraft.aircraft import Aircraft, Interesting
from Aircraft.tracker import AircraftTracker
from position import distance_nm, estimate_new_position
from tests.test_scoring import synthetic_plane


class MainCommandTests(unittest.TestCase):
    def run_commands(self, commands, ready=None, stdin="\n" * 20):
        tracker = AircraftTracker()
        stream = StringIO(stdin)
        with patch.object(main, "AircraftTracker", return_value=tracker), \
                patch.object(main, "load_aircraft", return_value=[]) as load, \
                patch.object(main, "show_planes"), \
                patch.object(main, "DEBUG", False), \
                patch.object(main, "sleep") as sleep, \
                patch.object(main.select, "select",
                             side_effect=ready if ready is not None else None,
                             return_value=([stream], [], [])), \
                patch.object(main.sys, "stdin", stream), \
                patch("builtins.input", side_effect=commands), \
                redirect_stdout(StringIO()) as console:
            main.main()
        return load.call_count, sleep.call_args_list, console.getvalue()

    def test_pause_commands_do_not_trigger_extra_receiver_updates(self):
        count, sleeps, text = self.run_commands([
            "interval 0.25", "cycles 3", "cycles all", "output all",
            "output suppressed", "output default", "resume", "q",
        ])
        self.assertEqual(count, 2)
        self.assertEqual([call.args[0] for call in sleeps], [1.0, 0.25])
        self.assertIn("Running indefinitely", text)
        self.assertIn("Changed output mode to default", text)

    def test_invalid_commands_stay_paused_and_keep_previous_interval(self):
        count, sleeps, text = self.run_commands([
            "interval nan", "interval inf", "interval 0", "interval 3601",
            "interval nope", "cycles 0", "cycles -1", "cycles 1.5",
            "output invalid", "unknown", "", "resume", "q",
        ])
        self.assertEqual(count, 2)
        self.assertEqual([call.args[0] for call in sleeps], [1.0, 1.0])
        self.assertEqual(text.count("Use interval 0.1-3600"), 8)
        self.assertIn("Valid output mode choices", text)

    def test_no_input_keeps_running_until_stdin_eof(self):
        count, _, _ = self.run_commands([], ready=[([], [], []), ([object()], [], [])], stdin="")
        self.assertEqual(count, 2)

    @unittest.expectedFailure
    def test_finite_cycle_budget_accepts_another_numeric_budget(self):
        # main.py uses int() as isinstance's second argument, raising TypeError.
        count, _, _ = self.run_commands(["cycles 1", "resume", "2", "q"])
        self.assertEqual(count, 2)

    @unittest.expectedFailure
    def test_eof_while_paused_exits_cleanly(self):
        self.run_commands([EOFError()])


class AircraftRuntimeTests(unittest.TestCase):
    def test_stopped_aircraft_reassessed_on_fifth_update(self):
        tracker = AircraftTracker()
        with patch("Aircraft.tracker.DEBUG", False):
            tracker.update_tracked_planes([synthetic_plane()])
            plane = tracker.current_planes[0]
            plane.stop_tracking()
            for cycle in range(1, 5):
                tracker.update_tracked_planes([synthetic_plane(track=180)])
                self.assertEqual(plane.stop_tracking_cycles, cycle)
                self.assertEqual(plane.interesting, Interesting.STOP_TRACKING)
                self.assertFalse(plane.distance_available)
                self.assertEqual(tracker.active, [])
            tracker.update_tracked_planes([synthetic_plane(track=180)])
        self.assertEqual(plane.interesting, Interesting.VERY_INTERESTING)
        self.assertTrue(plane.distance_available)
        self.assertEqual(tracker.active, [plane])
        self.assertEqual(plane.buffer_grace, 0)

    def test_callsign_changes_score_by_seven_and_a_half_points(self):
        with_flight = Aircraft(synthetic_plane(track=180))
        without_flight = Aircraft(synthetic_plane(track=180, flight=None))
        self.assertAlmostEqual(with_flight.score - without_flight.score, 7.5)
        self.assertEqual(with_flight.debug_score['flight avail.'], 2.5)
        self.assertEqual(without_flight.debug_score['flight avail.'], -5)

    def test_debug_output_after_expired_position_has_all_score_keys(self):
        plane = Aircraft(synthetic_plane(track=180))
        for _ in range(5):
            plane.update({"hex": plane.hex_code})
        with patch.object(output, "DEBUG", True), redirect_stdout(StringIO()) as text:
            output.show_planes([plane])
        self.assertIn("Flight Avail.: 0.0", text.getvalue())

    @unittest.expectedFailure
    def test_zero_groundspeed_is_ignored_without_comparing_missing_cpa(self):
        self.assertEqual(Aircraft(synthetic_plane(speed=0)).interesting, Interesting.IGNORE)

    @unittest.expectedFailure
    def test_debug_output_handles_aircraft_without_a_cpa(self):
        # main's closest/all display paths accept positioned planes without track.
        row = synthetic_plane()
        del row['track']
        plane = Aircraft(row)
        self.assertTrue(plane.distance_available)
        self.assertIsNone(plane.CPA['time_hr'])
        with patch.object(output, "DEBUG", True), redirect_stdout(StringIO()) as text:
            output.show_planes([plane])
        self.assertIn(plane.hex_code, text.getvalue())

    @unittest.expectedFailure
    def test_nonfinite_groundspeed_is_unavailable(self):
        plane = Aircraft(synthetic_plane(speed=float('nan')))
        self.assertFalse(plane.groundspeed_available)

    @unittest.expectedFailure
    def test_infinite_coordinate_is_unavailable(self):
        row = synthetic_plane()
        row['lat'] = float('inf')
        plane = Aircraft(row)
        self.assertFalse(plane.distance_available)

    @unittest.expectedFailure
    def test_two_missing_positions_advance_two_seconds_not_three(self):
        row = synthetic_plane(track=180)
        plane = Aircraft(row)
        missing = {key: value for key, value in row.items() if key not in ('lat', 'lon')}
        plane.update(missing)
        plane.update(missing)
        lat, lon = estimate_new_position(row['lat'], row['lon'], row['track'], row['gs'], 2)
        self.assertAlmostEqual(distance_nm(lat, lon, plane.lat, plane.lon), 0, places=8)


class ReaderTests(unittest.TestCase):
    def test_reads_aircraft_array(self):
        rows = [synthetic_plane()]
        with patch.object(adsb_reader, "AIRCRAFT_FILE") as path:
            path.open.return_value.__enter__.return_value = StringIO(json.dumps({'aircraft': rows}))
            self.assertEqual(adsb_reader.load_aircraft(), rows)

    def test_absent_aircraft_key_returns_empty_list(self):
        with patch.object(adsb_reader, "AIRCRAFT_FILE") as path:
            path.open.return_value.__enter__.return_value = StringIO('{}')
            self.assertEqual(adsb_reader.load_aircraft(), [])
