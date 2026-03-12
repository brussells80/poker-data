import requests
import json

BASE_URL = "https://www.npl.com.au/umbraco/surface/events/IndexEvents"

headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json"
}

games = []

for day in range(7):

    url = f"{BASE_URL}?dayOfWeek={day}"

    print("Getting day", day)

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print("Failed request:", r.status_code)
        continue

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
