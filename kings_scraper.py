import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

URL = "https://www.kingsroom.com.au/tournaments"

def scrape_kings():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    games = []

    today = datetime.now().strftime("%Y-%m-%d")

    rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")

        if len(cols) < 3:
            continue

        try:
            time = cols[0].text.strip()
            name = cols[1].text.strip()
            buyin = cols[2].text.strip()

            prize_pool = ""
            chips = ""

            if len(cols) > 3:
                prize_pool = cols[3].text.strip()

            if len(cols) > 4:
                chips = cols[4].text.strip()

            game = {
                "venue": "Kings",
                "date": today,
                "time": time,
                "name": name,
                "buyin": buyin,
                "prize_pool": prize_pool,
                "chips": chips
            }

            games.append(game)

        except:
            continue

    return games


if __name__ == "__main__":
    games = scrape_kings()

    print(json.dumps(games, indent=2))
