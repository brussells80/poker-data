import requests
from bs4 import BeautifulSoup
import json

url = "https://kingslive.com.au/"

response = requests.get(url)

soup = BeautifulSoup(response.text, "html.parser")

events = []

rows = soup.select("tr")

for row in rows:

    cols = row.find_all("td")

    if len(cols) < 5:
        continue

    events.append({
        "venue": "Kings",
        "time": cols[0].get_text(strip=True),
        "name": cols[1].get_text(strip=True),
        "buyin": cols[2].get_text(strip=True),
        "prize_pool": cols[3].get_text(strip=True),
        "chips": cols[4].get_text(strip=True)
    })

with open("kings_games.json", "w") as f:
    json.dump(events, f, indent=2)
