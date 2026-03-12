import requests
import json

url = "https://playapl.com/Umbraco/Api/event/searchevents"

states = {
    "NSW": 2,
    "QLD": 3,
    "VIC": 4,
    "SA": 5,
    "WA": 6,
    "ACT": 7,
    "NT": 8,
    "TAS": 9
}

games = []

for state, stateId in states.items():

    payload = {
        "venueId": None,
        "venueName": None,
        "suburb": None,
        "stateId": stateId,
        "brandId": 2,
        "buyIn": {"min": 0, "max": 210},
        "currentLat": -33.859,
        "currentLng": 151.218,
        "fromDate": None,
        "toDate": None,
        "guarantee": False,
        "mode": 1,
        "postcode": None,
        "regions": [],
        "showAllRegions": 0
    }

    print("Getting", state)

    r = requests.post(url, json=payload)
    data = r.json()

    for e in data:

        venue = e.get("venue", {})

        # Extract date
        date_time = e.get("dateTime")
        date = None
        if date_time:
            date = date_time.split("T")[0]

        # Extract late reg time
        late_reg_raw = e.get("lateRego")
        late_reg_time = None
        if late_reg_raw and " " in late_reg_raw:
            late_reg_time = late_reg_raw.split(" ")[1]

        games.append({
            "league": "APL",
            "state": e.get("stateName"),
            "name": e.get("description") or e.get("type"),
            "venue": venue.get("title"),
            "suburb": venue.get("suburb"),
            "date": date,
            "time": e.get("startTime"),
            "buyin": e.get("buyInDescription"),
            "guarantee": e.get("takeHomeAmount"),
            "late_reg": late_reg_time,
            "lat": venue.get("latitude"),
            "lng": venue.get("longitude")
        })

with open("apl_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "APL games")
