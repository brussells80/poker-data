import requests
from bs4 import BeautifulSoup
import json

URL = "https://kingslive.com.au"

headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(URL, headers=headers)

soup = BeautifulSoup(r.text, "html.parser")

games = []

rows = soup.select("tr")

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

    details = row.find_next("div")

    entries = None
    players = None
    late_reg = None
    date = None

    if details:

        lines = details.get_text("\n", strip=True).split("\n")

        for line in lines:

            if "Entries:" in line:
                entries = line.split(":")[1].strip()

            if "Players:" in line:
                players = line.split(":")[1].strip()

            if "Reg Ends:" in line:
                late_reg = line.split(":")[1].strip()

    date_header = row.find_previous("h4")
    if date_header:
        date = date_header.get_text(strip=True)

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
        "players_remaining": players
    })

with open("kings_live_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "Kings live games")
