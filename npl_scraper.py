import requests
from bs4 import BeautifulSoup
import json

base_url = "https://npl.com.au/Home/IndexEvents"

params = {
    "lat": -33.86,
    "lng": 151.21,
    "useLoc": 1,
    "state": "all"
}

games = []

for day in range(1,8):

    params["dayOfWeek"] = day

    r = requests.get(base_url, params=params)

    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.find_all("tr")

    for row in rows:

        cols = row.find_all(["td","th"])

        if len(cols) < 4:
            continue

        venue = cols[0].text.strip().split("(")[0]
        start = cols[1].text.strip()
        entry = cols[2].text.strip()
        game_type = cols[3].text.strip()

        games.append({
            "venue": venue,
            "start_time": start,
            "entry": entry,
            "type": game_type,
            "league": "NPL"
        })

with open("npl_games.json","w") as f:
    json.dump(games,f,indent=2)
