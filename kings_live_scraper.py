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

    if len(cols) < 6:
        continue

    start_time = cols[0].get_text(strip=True)
    name = cols[1].get_text(strip=True)
    buyin = cols[2].get_text(strip=True)
    guarantee = cols[3].get_text(strip=True)
    clock = cols[4].get_text(strip=True)
    chips = cols[5].get_text(strip=True)

    # grab full text block (contains entries/players etc)
    text = row.get_text(" ", strip=True)

    # entries
    entries = None
    m = re.search(r'Entries[:\s]*(\d+)', text)
    if m:
        entries = m.group(1)

    # players remaining
    players_remaining = None
    m = re.search(r'Players[:\s]*(\d+)', text)
    if m:
        players_remaining = m.group(1)

    # late reg
    late_reg = None
    m = re.search(r'Reg Ends[:\s]*(\d+)', text)
    if m:
        late_reg = m.group(1)

    # date (section header above table)
    date_header = row.find_previous("h4")
    date = date_header.get_text(strip=True) if date_header else None

    games.append({
        "league": "Kings",
        "series": "Live",
        "name": name,
        "venue": "Kings Live",
        "date": date,
        "start_time": start_time,
        "late_reg": late_reg,
        "buyin": buyin,
        "guarantee": guarantee,
        "clock": clock,
        "chips": chips,
        "entries": entries,
        "players_remaining": players_remaining
    })

with open("kings_live_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings live games")
