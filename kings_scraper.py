import requests
import json
import re
from datetime import datetime, timedelta

headers = {"User-Agent": "Mozilla/5.0"}

# dynamic 30-day range
today = datetime.today()
future = today + timedelta(days=30)

start = today.strftime("%Y-%m-%d")
end = future.strftime("%Y-%m-%d")

LIST_URL = f"https://api.kingspoker.com.au/api/v1/tournament/venue?1=date_g_{start}&2=date_le_{end}&exp=1*2&sort=date_asc:starttime_asc"

games = []

r = requests.get(LIST_URL, headers=headers)
tournaments = r.json()

for t in tournaments:

    description = t.get("description", "")

    # extract late reg time from text
    late_reg = None
    match = re.search(r'(\d{1,2}:\d{2})\s*pm?\s*late', description.lower())
    if match:
        late_reg = match.group(1)

    games.append({
        "league": "Kings",
        "name": t.get("title"),
        "venue": t.get("idvenue"),
        "date": t.get("date"),
        "time": t.get("starttime"),
        "buyin": t.get("price"),
        "guarantee": t.get("gtd"),
        "late_reg": late_reg,
        "entries": None,
        "players_remaining": None
    })

with open("kings_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings games")
