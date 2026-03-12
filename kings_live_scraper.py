import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://kingslive.com.au"

headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(URL, headers=headers)

soup = BeautifulSoup(r.text, "html.parser")

games = []

rows = soup.find_all("tr")

for row in rows:

    cols = row.find_all("td")

    if len(cols) < 4:
        continue

    name = cols[0].get_text(strip=True)
    clock = cols[1].get_text(strip=True)
    game_type = cols[2].get_text(strip=True)
    chips = cols[3].get_text(strip=True)

    row_text = row.get_text(" ", strip=True).lower()

    # entries
    entries = None
    m = re.search(r'entries\s*(\d+)', row_text)
    if m:
        entries = m.group(1)

    # players remaining
    players_remaining = None
    m = re.search(r'players\s*(\d+)', row_text)
    if m:
        players_remaining = m.group(1)

    # start time
    start_time = None
    m = re.search(r'\b\d{1,2}:\d{2}\s*(am|pm)', row_text)
    if m:
        start_time = m.group(0)

    # late reg
    late_reg = None
    m = re.search(r'late\s*rego\s*(\d{1,2}:\d{2})', row_text)
    if m:
        late_reg = m.group(1)

    games.append({
        "league": "Kings",
        "series": "Live",
        "name": name,
        "venue": "Kings Live",
        "start_time": start_time,
        "late_reg": late_reg,
        "clock": clock,
        "type": game_type,
        "chips": chips,
        "entries": entries,
        "players_remaining": players_remaining
    })

with open("kings_live_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings live games")
