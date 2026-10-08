# Scoring review at 7609933

Run the suite from the repository root:

```sh
python -B -m unittest discover -s tests -v
```

The suite runs 24 tests: 20 pass normally and four are marked as expected
failures for the findings below. Expected failures keep the unresolved behavior
visible without requiring changes to production files. They should be removed
when those findings are resolved or the intended policy is clarified.

## Comparison and interpretation

`scoring_baselines.py` freezes the actual scoring methods from `0b87ae4` (the
original refactor repair) and `942aab3` (immediately before the latest modifiers).
The tests substitute only the scoring method, leaving receiver parsing and
position calculations identical. The frozen methods were checked against the
historical implementations on all 731 records in samples 1 through 9; both
classifications and scores matched. Running the committed tests requires no Git
history, network connection, or additional dependencies.

Samples 5 through 9 contain 542 aircraft observations, including repeated
aircraft across snapshots. The snapshots have no human interest labels, so the
tests use a documented viewing proxy independent of assigned scores/states:

- Within 10 nm, at or below 10,000 ft, and above 150 kt.
- Within 4 nm and below 30,000 ft, with a projected pass within 2 nm in the next
  three minutes, and above 150 kt.
- Within 4 nm and at or below 7,500 ft, including slow aircraft.

All criteria require usable position, altitude, speed, and relational data.
"Selected" means INTERESTING or VERY_INTERESTING; WATCHLIST is not counted.

| Sample | Observations | Viewing candidates | Previous selections | Current selections | Current candidate hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| sample5 | 134 | 0 | 2 | 0 | 0 |
| sample6 | 131 | 0 | 2 | 0 | 0 |
| sample7 | 94 | 1 | 2 | 1 | 1 |
| sample8 | 108 | 0 | 4 | 0 | 0 |
| sample9 | 75 | 2 | 4 | 2 | 2 |
| Total | 542 | 3 | 14 | 3 | 3 |

The three candidates are PDT5959 (`a857c2`, sample7), EDV5057 (`a2af3e`, sample9),
and PDT5911 (`a944b9`, sample9). The first two are nearby low aircraft; the third
is a close, imminent overhead pass. The original refactor classified none of
them as interesting. Both the pre-modifier and current versions classify all
three as interesting.

Consequently, the latest modifiers improve selection precision under this
proxy from 3/14 to 3/3, preserving candidate coverage. They do **not** demonstrate
an increase in interesting classifications over the immediately preceding
version on these samples. The older refactor comparison does show improved
coverage, from 0/3 to 3/3. Three positive observations are too few to establish
general real-world accuracy, and these proxy labels are not human judgments.

The synthetic tests separately exercise 18 nearby low departure scenarios
(2/4/6 nm, 1,000/2,000 ft, 180/220/280 kt, heading away with a callsign). All
score between 10 and 20: the previous method assigned WATCHLIST and the current
method assigns INTERESTING. Additional tests cover distant/high cruise,
initially missing data, and expired positions.

## Logic findings

1. **Landing promotion blocked in the 10–20 band (`aircraft.py:256`).**
   `low_speed and (not possible_airliner_climb or not possible_airliner_land)`
   blocks every low-speed landing candidate. Climb requires speed above 160 kt;
   landing requires speed at most 150 kt, so both predicates cannot be true.
   Their negations joined with `or` therefore always evaluate true. A 140 kt,
   2,000 ft aircraft 6 nm away reproduces the missed promotion. If the intent is
   to exclude low-speed aircraft satisfying neither pattern, this Boolean
   condition needs reconsideration, along with the separate <=120 kt override.

2. **Missing-data guard can fall through (`aircraft.py:197–202`).**
   For an already watchlisted/interesting aircraft, unavailable data younger
   than five cycles does not return from this block. Updating a previously
   interesting object with `persistent=False` and missing fields therefore
   reaches `self.speed_kts <= 120` with speed None and raises TypeError.
   The tracker normally updates existing aircraft with persistence enabled;
   the reproducer exercises the supported nonpersistent update path. The
   unavailable-data block needs an explicit outcome for every path.

3. **Distance and altitude limits depend on the score band (`aircraft.py:254–272`).**
   Scores below 30 apply the >=15 nm and >=30,000 ft limits; the >=30 branch
   ignores both for speeds above 150 kt. Synthetic inbound aircraft at
   33,000 ft / 2 nm and 1,000 ft / 30 nm both become VERY_INTERESTING. Two
   expected-failure tests assume those limits should apply across score bands.
   If very high scores are deliberately allowed to override the limits, these
   two expectations should instead be changed to document that exception.

All Python files syntax-check successfully, and all new sample observations
score without exceptions on their initial update. No production code was
changed as part of this review.
