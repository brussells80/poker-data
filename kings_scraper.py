import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

URL = "https://www.kingsroom.com.au/tournaments"


def extract_field(text, label):
    try:
        pattern = rf"{label}:(.*?)(?=[A-Z][a-zA-Z ]*:|$)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    except:
        pass
    return None


def scrape_kings():

    games = []

    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print("Failed to load Kings page:", e)
        return games

    soup = BeautifulSoup(response.text, "html.parser")

    today = datetime.now().strftime("%Y-%m-%d")

    rows = soup.find_all("tr")

    for row in rows:

        cols = row.find_all("td")

        if len(cols) < 3:
            continue

        try:

            name = cols[0].get_text(strip=True)
            time = cols[1].get_text(strip=True)
            details = cols[2].get_text(strip=True)

            buyin = extract_field(details, "Buy-In")
            prize_pool = extract_field(details, "Prize Pool")
            chips = extract_field(details, "Chips")
            entries = extract_field(details, "Entries")
            players = extract_field(details, "Players")
            gtd = extract_field(details, "GTD")

            games.append({
                "venue": "Kings",
                "name": name,
                "date": today,
                "time": time,
                "buyin": buyin,
                "prize_pool": prize_pool,
                "chips": chips,
                "entries": entries,
                "players_remaining": players,
                "guarantee": gtd
            })

        except Exception as e:
            print("Skipping row:", e)
            continue

    return games


if __name__ == "__main__":

    games = scrape_kings()

    try:
        with open("kings_games.json", "w") as f:
            json.dump(games, f, indent=2)
        print(f"Saved {len(games)} Kings games")
    except Exception as e:
        print("Failed to save JSON:", e)
