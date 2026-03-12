import requests
import json

games = []

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# -------------------------
# WEEKLY KINGS TOURNAMENTS
# -------------------------

weekly_url = "https://kingspoker.com.au/wp-json/wp/v2/tournaments?per_page=100"

try:
    r = requests.get(weekly_url, headers=headers)
    data = r.json()

    for e in data:

        games.append({
            "league": "Kings",
            "series": "Weekly",
            "name": e.get("title", {}).get("rendered"),
            "venue": e.get("acf", {}).get("venue"),
            "date": e.get("acf", {}).get("date"),
            "time": e.get("acf", {}).get("start_time"),
            "buyin": e.get("acf", {}).get("buyin"),
            "guarantee": e.get("acf", {}).get("guarantee"),
            "late_reg": e.get("acf", {}).get("late_reg"),
            "entries": None,
            "players_remaining": None
        })

except Exception as e:
    print("Weekly Kings failed:", e)


# -------------------------
# KINGS LIVE SERIES
# -------------------------

live_url = "https://kingslive.com.au/api/tournaments"

try:

    r = requests.get(live_url, headers=headers)
    data = r.json()

    for e in data:

        games.append({
            "league": "Kings",
            "series": "Live",
            "name": e.get("name"),
            "venue": e.get("venue"),
            "date": e.get("date"),
            "time": e.get("start_time"),
            "buyin": e.get("buyin"),
            "guarantee": e.get("guarantee"),
            "late_reg": e.get("late_reg"),
            "entries": e.get("entries"),
            "players_remaining": e.get("players_remaining")
        })

except Exception as e:
    print("Kings live failed:", e)


# -------------------------
# SAVE OUTPUT
# -------------------------

with open("kings_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings games")
