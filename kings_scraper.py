import requests
import json

LIST_URL = "https://api.kingspoker.com.au/api/v1/tournament/venue?1=date_g_2026-3-12&2=date_le_2026-3-26&exp=1*2&sort=date_asc:starttime_asc"

headers = {
    "User-Agent": "Mozilla/5.0"
}

games = []

r = requests.get(LIST_URL, headers=headers)
tournaments = r.json()

for t in tournaments:

    tid = t["idtournament"]

    detail_url = f"https://api.kingspoker.com.au/api/v1/tournament/{tid}"

    try:
        d = requests.get(detail_url, headers=headers).json()

        games.append({
            "league": "Kings",
            "name": d.get("name"),
            "venue": d.get("venue"),
            "date": d.get("date"),
            "time": d.get("starttime"),
            "buyin": d.get("buyin"),
            "guarantee": d.get("guarantee"),
            "late_reg": d.get("latereg"),
            "entries": None,
            "players_remaining": None
        })

    except:
        pass

with open("kings_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings games")
