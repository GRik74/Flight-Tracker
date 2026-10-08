# Visibility scoring and regression checks

Run from the repository root:

```sh
python -B -m unittest discover -s tests -v
```

The suite now runs 36 tests with no expected failures. The four findings from
reviewing 7609933 are ordinary passing regression tests. Production changes are
confined to Aircraft.update_interesting() and one standard-library import; the
score formula, aircraft fields, tracker lifecycle, and application structure
remain in place.

## Visibility policy

The user's definition is naked-eye visibility now or shortly, generally below
10,000 ft, within 8 nm, and between 180 and 300 kt. The implementation uses:

- At or below 10,000 ft and within 8 nm as the current viewing region.
- Inbound aircraft up to 15 nm away as candidates if their projected closest
  approach is within 8 nm and occurs in the next five minutes. Altitude must
  still be at or below 10,000 ft; no vertical-position extrapolation was added.
- 180–300 kt as the preferred speed band. These aircraft are INTERESTING even
  when the raw score is low because they are already visible but moving away.
  Scores of 30 or more make them VERY_INTERESTING inside the visibility limits.
- Nearby climbs of at least 300 ft/min at 160–300 kt (excluding exactly 160),
  and descents of at least 300 ft/min at 120–300 kt, as VERY_INTERESTING.
  Barometric rate is preferred, with geometric rate as a fallback. These are
  airport-movement indicators, not confirmation of a particular airport.
- Slow potential final approaches at 120–180 kt (excluding exactly 180) below
  7,500 ft as INTERESTING when rate is unavailable and a nonempty callsign is
  present. This preserves a limited approach heuristic without treating the
  callsign as proof of climb or descent. With an available level-flight rate,
  this exception does not apply.
- Very close low aircraft within 2.5 nm, below 7,500 ft, and between 60 and
  180 kt (exclusive endpoints) as another limited INTERESTING exception.

Visibility limits run before promotions, so high scores and receiver climb/
descent rates cannot promote distant or high aircraft outside the viewing
region. Grounded or stationary aircraft are ignored.

## Missing data and modifier fixes

Every unavailable-data path returns before numeric scoring. An already active
classification is held during a short data gap without recalculating or
promoting it. Once any required data age reaches five cycles and data is
unavailable, it becomes WATCHLIST. Previously uninteresting aircraft stay
NOT_INTERESTING when data is unavailable. Scores/debug components are reset on
these paths. Existing receiver persistence and availability thresholds remain.

This prevents the nonpersistent missing-field TypeError. It also eliminates the
unreachable landing promotion by applying distinct visibility and airport
conditions rather than the conflicting climb/landing Boolean expression.
The altitude, range, and speed restrictions apply regardless of score band.
Malformed or nonfinite optional vertical rates do not trigger promotions.

## Sample evidence

The frozen methods from 0b87ae4 and 942aab3 remain in scoring_baselines.py.
Only the scoring method is substituted during comparison; parsing and position
calculations are identical. No Git history or network is required to run tests.
The earlier validation matched these references to their historical versions
on all 731 sample observations.

Under the clarified visibility definition, samples 5–9 contain one candidate:
N191CZ (a16c2c, sample5), descending at 768 ft/min, at 800 ft, 6.81 nm away,
and 140.1 kt. Both historical baselines, and the unfixed 7609933 modifiers,
missed this aircraft. The repair selects it as VERY_INTERESTING.

| Sample | Observations | Visibility candidates | Pre-modifier selections (942aab3) | Fixed selections | Fixed candidate hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| sample5 | 134 | 1 | 2 | 1 | 1 |
| sample6 | 131 | 0 | 2 | 0 | 0 |
| sample7 | 94 | 0 | 2 | 0 | 0 |
| sample8 | 108 | 0 | 4 | 0 | 0 |
| sample9 | 75 | 0 | 4 | 0 | 0 |
| Total | 542 | 1 | 14 | 1 | 1 |

The earlier review's three targets no longer satisfy the clarified criteria:
PDT5959 and EDV5057 remain outside 8 nm and their projected passes also stay
outside 8 nm; PDT5911 is at 25,950 ft. They now remain WATCHLIST.

Samples 2 and 4 contribute five more nearby climb/descent candidates, all now
selected. Across all nine snapshots the fix captures all six candidates under
these criteria, versus two captured by the pre-modifier reference. Tests assert
these individual aircraft as well as aggregate new-sample coverage. The suite
also replays all nine snapshots through AircraftTracker for 35 cycles each to
check classification and retention interaction.

Synthetic cases exercise 18 nearby departures, slow approaches, reported
climb/descent with and without callsigns, rate fallbacks, visibility and speed
boundaries, imminent passes, ground cases, partial/nonpersistent missing fields,
and scores above 30 outside the permitted region.

These are receiver-data indicators of visibility, not human observations.
Weather, terrain, obstruction, aircraft size, and actual airport locations are
not modeled. The supplied snapshots contain few qualifying positive cases;
the synthetic cases cover the boundary and behavior combinations missing from
them.
