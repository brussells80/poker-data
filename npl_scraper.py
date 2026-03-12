import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

URL = "https://www.npl.com.au/todays-league-events/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

def scrape_npl():

    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    today = datetime.now().strftime("%Y-%m-%d")

    games = []

    table = soup.find("table")

    if not table:
        print("No NPL table found")
        return games

    tbody = table.find("tbody")

    for row in tbody.find_all("tr"):

        cols = row.find_all("td")

        if len(cols) < 4:
            continue

        venue = cols[0].get_text(strip=True)
        start_time = cols[1].get_text(strip=True)
        entry = cols[2].get_text(strip=True)
        game_type = cols[3].get_text(strip=True)

        # remove distance text like "(44.0 KM)"
        if "(" in venue:
            venue = venue.split("(")[0].strip()

        game = {
            "league": "NPL",
            "state": None,
            "name": game_type,
            "venue": venue,
            "suburb": None,
            "date": today,
            "time": start_time,
            "buyin": entry,
            "guarantee": None,
            "late_reg": None,
            "lat": None,
            "lng": None
        }

        games.append(game)

    return games


games = scrape_npl()

with open("npl_games.json", "w") as f:
    json.dump(games, f, indent=2)

print("Saved", len(games), "NPL games")
