import requests
import json
from datetime import datetime, timedelta

headers = {
    "User-Agent": "Mozilla/5.0"
}

# dynamic date range (today → 30 days)
today = datetime.today()
future = today + timedelta(days=30)

start = today.strftime("%Y-%m-%d")
end = future.strftime("%Y-%m-%d")

LIST_URL = f"https://api.kingspoker.com.au/api/v1/tournament/venue?1=date_g_{start}&2=date_le_{end}&exp=1*2&sort=date_asc:starttime_asc"

games = []

r = requests.get(LIST_URL, headers=headers)
tournaments = r.json()

for t in tournaments:

    tid = t["idtournament"]

    detail_url = f"https://api.kingspoker.com.au/api/v1/tournament/details/{tid}"

    try:
        d = requests.get(detail_url, headers=headers).json()

        games.append({
            "league": "Kings",
            "name": d.get("name"),
            "venue": d.get("venue_name"),
            "date": d.get("date"),
            "time": d.get("starttime"),
            "buyin": d.get("buyin"),
            "guarantee": d.get("guarantee"),
            "late_reg": d.get("late_reg"),
            "entries": d.get("entries"),
            "players_remaining": d.get("players_remaining")
        })

    except Exception as e:
        print("Failed tournament", tid)

with open("kings_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings games")
