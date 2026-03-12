import requests
import json
from datetime import datetime

BASE_URL = "https://www.npl.com.au/umbraco/surface/eventsurface/IndexEvents"

headers = {
    "User-Agent": "Mozilla/5.0"
}

games = []

today = datetime.now()

for day in range(7):

    url = f"{BASE_URL}?dayOfWeek={day}"

    print("Getting day", day)

    r = requests.get(url, headers=headers)
    data = r.json()

    for e in data:

        games.append({
            "league": "NPL",
            "state": e.get("State"),
            "name": e.get("Name"),
            "venue": e.get("Venue"),
            "suburb": e.get("Suburb"),
            "date": e.get("Date"),
            "time": e.get("StartTime"),
            "buyin": e.get("Entry"),
            "guarantee": e.get("Guarantee"),
            "late_reg": None,
            "lat": None,
            "lng": None
        })

with open("npl_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "NPL games")
