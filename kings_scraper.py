import requests
import json

url = "https://kingslive.com.au/api/events"

response = requests.get(url)
data = response.json()

events = []

for e in data:

    events.append({
        "venue": "Kings",
        "name": e.get("name"),
        "start_time": e.get("start"),
        "buyin": e.get("buyin"),
        "guarantee": e.get("guarantee"),
        "entries": e.get("entries"),
        "players_remaining": e.get("players"),
        "late_reg_level": e.get("late_reg"),
        "chips": e.get("chips")
    })

with open("kings_games.json", "w") as f:
    json.dump(events, f, indent=2)
