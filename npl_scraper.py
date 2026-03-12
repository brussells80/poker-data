import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

URL = "https://www.npl.com.au/todays-league-events/"

def scrape_npl():

    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    today = datetime.now().strftime("%Y-%m-%d")

    games = []

    table = soup.find("table")

    if table is None:
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
            "venue": venue,
            "date": today,
            "start_time": start_time,
            "entry": entry,
            "type": game_type,
            "league": "NPL"
        }

        games.append(game)

    return games


if __name__ == "__main__":

    games = scrape_npl()

    with open("npl_games.json", "w") as f:
        json.dump(games, f, indent=2)

    print("Saved", len(games), "NPL games")
