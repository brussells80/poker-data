import requests
import json

url = "https://kingslive.com.au/Home/GetSchedule"

response = requests.get(url)

data = response.json()

events = []

for e in data:

    events.append({
        "venue": "Kings",
        "name": e.get("Name"),
        "start_time": e.get("Start"),
        "buyin": e.get("BuyIn"),
        "guarantee": e.get("GTD"),
        "chips": e.get("Stack"),
        "clock": e.get("Clock"),
        "type": e.get("Type")
    })

with open("kings_games.json", "w") as f:
    json.dump(events, f, indent=2)
