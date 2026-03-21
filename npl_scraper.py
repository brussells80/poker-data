import json
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.npl.com.au/"


def clean_text(text):
    return text.strip().replace("\n", "").replace("\t", "")


def parse_venue(venue_text):
    """
    Example:
    'PETERSHAM RSL, SYDNEY MARRICKVILLE, NSW (7.6 KM)'
    """
    parts = venue_text.split(",")

    venue = parts[0].title()

    suburb = ""
    state = ""

    if len(parts) > 1:
        suburb = parts[1].strip().title()

    if len(parts) > 2:
        state = parts[2].strip().split(" ")[0]

    return venue, suburb, state


def parse_buyin(entry_text):
    entry_text = entry_text.upper()

    if "FREE" in entry_text:
        return 0

    try:
        return int(entry_text.replace("$", "").replace(".00", "").strip())
    except:
        return None


def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Required for GitHub Actions
    options.binary_location = "/usr/bin/chromium-browser"

    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=options)

    return driver


def scrape_npl():
    driver = setup_driver()
    driver.get(URL)

    time.sleep(6)  # allow JS to render

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    games = []

    today = datetime.now().strftime("%Y-%m-%d")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")

        if len(cols) < 4:
            continue

        venue_text = clean_text(cols[0].text)
        start_text = clean_text(cols[1].text)
        entry_text = clean_text(cols[2].text)
        type_text = clean_text(cols[3].text)

        venue, suburb, state = parse_venue(venue_text)

        game = {
            "league": "NPL",
            "state": state,
            "name": f"{venue} {start_text}",
            "venue": venue,
            "suburb": suburb,
            "date": today,
            "time": start_text,
            "buyin": parse_buyin(entry_text),
            "guarantee": None,
            "late_reg": None,
            "type": type_text,
            "lat": None,
            "lng": None
        }

        games.append(game)

    driver.quit()

    return games


def main():
    games = scrape_npl()

    with open("npl_games.json", "w") as f:
        json.dump(games, f, indent=2)

    print(f"Scraped {len(games)} NPL games")


if __name__ == "__main__":
    main()
