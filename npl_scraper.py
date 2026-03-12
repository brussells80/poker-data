import requests
import json

BASE_URL = "https://www.npl.com.au/umbraco/surface/eventsurface/IndexEvents"

headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

games = []

for day in range(7):

    print("Getting day", day)

    payload = {
        "dayOfWeek": day
    }

    r = requests.post(BASE_URL, json=payload, headers=headers)

    if r.status_code != 200:
        print("Failed request:", r.status_code)
        continue

    try:
        data = r.json()
    except:
        print("Invalid JSON")
        continue

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
