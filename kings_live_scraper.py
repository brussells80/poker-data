import requests
from bs4 import BeautifulSoup
import json

URL = "https://kingslive.com.au/results"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(URL, headers=headers)

soup = BeautifulSoup(r.text, "html.parser")

games = []

rows = soup.find_all("tr")

for row in rows:

    cols = row.find_all("td")

    if len(cols) < 5:
        continue

    name = cols[0].get_text(strip=True)
    prize_pool = cols[1].get_text(strip=True)
    clock = cols[2].get_text(strip=True)
    game_type = cols[3].get_text(strip=True)
    chips = cols[4].get_text(strip=True)

    games.append({
        "league": "Kings",
        "series": "Live",
        "name": name,
        "venue": "Kings Live",
        "prize_pool": prize_pool,
        "clock": clock,
        "type": game_type,
        "chips": chips
    })

with open("kings_live_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings live games")
