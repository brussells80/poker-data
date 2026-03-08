import requests
import json
from bs4 import BeautifulSoup

url = "https://kingslive.com.au/"

r = requests.get(url)
soup = BeautifulSoup(r.text, "html.parser")

events = []

rows = soup.select("table tbody tr")

for row in rows:
    cols = row.find_all("td")
    
    if len(cols) < 6:
        continue

    time = cols[0].text.strip()
    name = cols[1].text.strip()
    buyin = cols[2].text.strip()
    prize_pool = cols[3].text.strip()
    clock = cols[4].text.strip()
    type_game = cols[5].text.strip()
    chips = cols[6].text.strip()

    events.append({
        "venue": "Kings",
        "time": time,
        "name": name,
        "buyin": buyin,
        "prize_pool": prize_pool,
        "clock": clock,
        "type": type_game,
        "chips": chips
    })

with open("kings_games.json", "w") as f:
    json.dump(events, f, indent=2)
