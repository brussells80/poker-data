import requests
import json
from bs4 import BeautifulSoup

url = "https://kingslive.com.au/"

r = requests.get(url)
soup = BeautifulSoup(r.text, "html.parser")

events = []

rows = soup.select(".schedule-row")

for row in rows:

    cols = row.find_all("div")

    if len(cols) < 7:
        continue

    events.append({
        "venue": "Kings",
        "time": cols[0].get_text(strip=True),
        "name": cols[1].get_text(strip=True),
        "buyin": cols[2].get_text(strip=True),
        "prize_pool": cols[3].get_text(strip=True),
        "clock": cols[4].get_text(strip=True),
        "type": cols[5].get_text(strip=True),
        "chips": cols[6].get_text(strip=True)
    })

with open("kings_games.json", "w") as f:
    json.dump(events, f, indent=2)
