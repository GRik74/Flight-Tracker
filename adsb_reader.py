import json
from pathlib import Path

AIRCRAFT_FILE = Path("/run/dump1090-fa/aircraft.json")

def load_aircraft():
    with AIRCRAFT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

        return data.get("aircraft", [])
    