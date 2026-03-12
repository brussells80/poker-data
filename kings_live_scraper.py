import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://kingslive.com.au"
headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(URL, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")

games = []

rows = soup.select("table tbody tr")

for row in rows:

    cols = row.find_all("td")

    # skip rows without the main columns
    if len(cols) < 7:
        continue

    start_time = cols[0].get_text(strip=True)
    name = cols[1].get_text(strip=True)
    buyin = cols[2].get_text(strip=True)
    guarantee = cols[3].get_text(strip=True)
    clock = cols[4].get_text(strip=True)
    game_type = cols[5].get_text(strip=True)
    chips = cols[6].get_text(strip=True)

    # full row text (contains entries / players etc)
    text = row.get_text(" ", strip=True)

    entries = None
    players_remaining = None
    late_reg = None

    m = re.search(r'Entries:\s*(\d+)', text)
    if m:
        entries = m.group(1)

    m = re.search(r'Players:\s*(\d+)', text)
    if m:
        players_remaining = m.group(1)

    m = re.search(r'Reg Ends:\s*(\d+)', text)
    if m:
        late_reg = m.group(1)

    # find the date header above the table
    date_header = row.find_previous("h4")
    date = date_header.get_text(strip=True) if date_header else None

    games.append({
        "league": "Kings",
        "series": "Live",
        "name": name,
        "venue": "Kings Live",
        "date": date,
        "start_time": start_time,
        "buyin": buyin,
        "guarantee": guarantee,
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
