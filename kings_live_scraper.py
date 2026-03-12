import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://kingslive.com.au/results"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(URL, headers=headers)

soup = BeautifulSoup(r.text, "html.parser")

games = []

events = soup.find_all("div", class_="event")

for e in events:

    text = e.get_text(" ", strip=True)

    # Tournament name
    name_tag = e.find("h3")
    name = name_tag.get_text(strip=True) if name_tag else None

    # Buy-in
    buyin = None
    m = re.search(r"\$\d+\s*buy", text.lower())
    if m:
        buyin = m.group(0)

    # Guarantee
    guarantee = None
    m = re.search(r"\$\d[\d,]*\s*gtd", text.lower())
    if m:
        guarantee = m.group(0)

    # Start time
    start_time = None
    m = re.search(r"\b\d{1,2}:\d{2}\s*(am|pm)", text.lower())
    if m:
        start_time = m.group(0)

    # Late reg
    late_reg = None
    m = re.search(r"late.*?(\d{1,2}:\d{2})", text.lower())
    if m:
        late_reg = m.group(1)

    # Entries
    entries = None
    m = re.search(r"entries\s*(\d+)", text.lower())
    if m:
        entries = m.group(1)

    # Players remaining
    players_remaining = None
    m = re.search(r"players\s*(\d+)", text.lower())
    if m:
        players_remaining = m.group(1)

    games.append({
        "league": "Kings",
        "series": "Live",
        "name": name,
        "venue": "Kings Live",
        "buyin": buyin,
        "guarantee": guarantee,
        "start_time": start_time,
        "late_reg": late_reg,
        "entries": entries,
        "players_remaining": players_remaining
    })

with open("kings_live_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings live games")
