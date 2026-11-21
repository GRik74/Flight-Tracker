import json, logging
from time import monotonic, localtime, asctime
from pathlib import Path
from os import replace

logger = logging.getLogger(__name__)

temp_file = Path("/home/grik74/flight-tracker/temp.json")
interesting_planes = Path("/home/gik74/flight-tracker/aircraft.json")
tracked_planes = Path("/home/grik74/flight-tracker/tracker.json")
error_file = Path("/home/grik74/flight-tracker/errors.log")

DEBUG = True

# def setup_logger():
#     logging.basicConfig(filename = )

def show_planes(planes):
    for plane in planes:
        try:
            _show_planes([plane])
        except (TypeError, ValueError, KeyError, ArithmeticError, OSError) as error:
            dump_error_info(error, f"Displaying aircraft {plane.hex_code}",
                            severity="WARNING", tracked_planes=planes)


def _show_planes(planes):
    for plane in planes:
        plane_info = f"Hex Code: {plane.hex_code:7}"
        plane_info += f"| {plane.flight:10}" if not plane.flight is None else ""
        if plane.distance_available: plane_info += f" | Dist.: {str(round(plane.dist_nm, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4}"
        if plane.relational_info_available: plane_info += f" | Track: {str(int(round(plane.track, 0))):>4}"
        plane_info += f" | Alt: {str(round(plane.alt_ft, 1)):>7} ft" if plane.altitude_available else f" | Alt: {'unknown':>7} ft"
        plane_info += f" | GS: {str(int(round(plane.speed_kts, 0))):>8} kts" if plane.groundspeed_available else f" | GS: {'unknown':>8} kts"

        print(plane_info)
        if DEBUG: print(f"""------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 
DEBUG: {plane.hex_code} | Age: {plane.age} | Missing from receiver: {plane.missing_from_receiver} | Buffer grace: {plane.buffer_grace} | Interesting: {plane.interesting} \n
Time to CPA: {round(plane.CPA['time_hr']*60, 0)} mins | Dist_nm at CPA: {round(plane.CPA['dist_nm'], 1)} nm | Bearing at CPA: {round(plane.CPA['bearing'], 0)} deg.

Score:
Flight Avail.: {plane.debug_score['flight avail.']}
Proximity:     {round(plane.debug_score['proximity score'], 1)}
Altitude:      {round(plane.debug_score['altitude score'], 1)}
Closing Prox.: {round(plane.debug_score['closing prox. score'], 1)}
Closing Time:  {round(plane.debug_score['closing time score'], 1)}

Total Score:   {round(plane.score, 1)}
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
""")

# Increase this to retain more routine snapshots. Error snapshots are never rotated.
SNAPSHOT_RETENTION = 5
LOG_DIRECTORY = Path(__file__).resolve().parent / "Logging"


def _serialize(value):
    from enum import Enum
    from math import isfinite
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, float) and not isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__dict__"):
        return _serialize(vars(value))
    return repr(value)


def _timestamp():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _save_snapshot(path, payload):
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(_serialize(payload), file, indent=2, allow_nan=False)
            file.flush()
        replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_output(interesting_planes, tracked_planes, *, keep=None, directory=None):
    """Atomically save a snapshot; keep=None uses SNAPSHOT_RETENTION.

    Increase SNAPSHOT_RETENTION to keep more history. Only snapshot-*.json
    files in the routine snapshots directory are eligible for removal.
    Returns the saved path, or None after logging a storage failure.
    """
    keep = SNAPSHOT_RETENTION if keep is None else keep
    if not isinstance(keep, int) or isinstance(keep, bool) or keep < 1:
        raise ValueError("keep must be a positive integer")
    directory = Path(directory) if directory is not None else LOG_DIRECTORY / "snapshots"
    stamp = _timestamp()
    path = directory / f"snapshot-{stamp}.json"
    try:
        _save_snapshot(path, {"timestamp": stamp, "tracked_planes": tracked_planes,
                              "interesting_planes": interesting_planes})
        for old in sorted(directory.glob("snapshot-*.json"), reverse=True)[keep:]:
            old.unlink()
        return path
    except (OSError, TypeError, ValueError) as error:
        dump_error_info(error, "Saving/rotating aircraft snapshots", severity="ERROR",
                        tracked_planes=tracked_planes)
        return None


def dump_error_info(error, cause, *, severity="ERROR", handled=True,
                    tracked_planes=None, directory=None):
    """Append an error block, including handled exceptions and traceback.

    WARNING and above preserve an independent aircraft snapshot when supplied.
    Persistence failures fall back to stderr, never masking the original error.
    Callers assign severity and report handled=False before re-raising a crash.
    """
    import sys
    import traceback
    directory = Path(directory) if directory is not None else LOG_DIRECTORY
    stamp = _timestamp()
    level = str(severity).upper()
    record = {"timestamp": stamp, "type": type(error).__name__,
              "severity": level, "handled": handled,
              "outcome": "handled" if handled else "crash",
              "cause": str(cause), "message": str(error),
              "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__))}
    if tracked_planes is not None and level in ("WARNING", "ERROR", "CRITICAL"):
        snapshot = directory / "errors" / f"{stamp}.json"
        try:
            _save_snapshot(snapshot, {"timestamp": stamp, "tracked_planes": tracked_planes})
            record["snapshot"] = str(snapshot)
        except Exception as snapshot_error:
            record["snapshot_error"] = f"{type(snapshot_error).__name__}: {snapshot_error}"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "errors.log").open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n\n")
            file.flush()
    except Exception as log_error:
        print(f"Unable to persist error: {log_error}; {record}", file=sys.stderr)
    return record
