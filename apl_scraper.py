import json
import os
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.npl.com.au/"


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def parse_buyin(entry_text):
    text = clean_text(entry_text).upper()

    if not text:
        return None

    if "FREE" in text:
        return 0

    match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]{1,2})?)", text)
    if not match:
        return None

    value = match.group(1)
    try:
        return float(value) if "." in value else int(value)
    except Exception:
        return None


def parse_venue(venue_text):
    venue_text = clean_text(venue_text)

    distance = None
    distance_match = re.search(r"\(([\d.]+)\s*KM\)", venue_text, re.IGNORECASE)
    if distance_match:
        try:
            distance = float(distance_match.group(1))
        except Exception:
            distance = None

    venue_without_distance = re.sub(
        r"\([\d.]+\s*KM\)",
        "",
        venue_text,
        flags=re.IGNORECASE
    ).strip()

    parts = [p.strip() for p in venue_without_distance.split(",") if p.strip()]

    venue = parts[0].title() if len(parts) > 0 else ""
    suburb = parts[1].title() if len(parts) > 1 else ""
    state = parts[2].split()[0].upper() if len(parts) > 2 else ""

    return venue, suburb, state, distance


def make_game(venue_text, start_text, entry_text, type_text):
    venue, suburb, state, distance = parse_venue(venue_text)

    return {
        "league": "NPL",
        "state": state,
        "name": f"{venue} {clean_text(start_text)}".strip(),
        "venue": venue,
        "suburb": suburb,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": clean_text(start_text),
        "buyin": parse_buyin(entry_text),
        "guarantee": None,
        "late_reg": None,
        "type": clean_text(type_text),
        "distance_km": distance,
        "lat": None,
        "lng": None
    }


def get_existing_path(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def setup_driver():
    chrome_binary = get_existing_path([
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium",
    ])

    chromedriver_path = get_existing_path([
        "/usr/bin/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
        "/usr/lib/chromium/chromedriver",
    ])

    if not chrome_binary:
        raise RuntimeError("Could not find Chromium binary on runner")

    if not chromedriver_path:
        raise RuntimeError("Could not find chromedriver on runner")

    options = Options()
    options.binary_location = chrome_binary
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1800,3200")

    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)


def click_text_if_found(driver, text):
    xpath = (
        f"//*[self::button or self::a or self::div or self::span]"
        f"[normalize-space()='{text}']"
    )
    elems = driver.find_elements(By.XPATH, xpath)

    for elem in elems:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", elem)
            time.sleep(1.0)
            return True
        except Exception:
            continue

    return False


def extract_games_from_rows(driver):
    games = []
    seen = set()

    row_candidates = driver.find_elements(By.XPATH, "//tr[td]")
    for row in row_candidates:
        try:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 4:
                continue

            venue_text = clean_text(cols[0].text)
            start_text = clean_text(cols[1].text)
            entry_text = clean_text(cols[2].text)
            type_text = clean_text(cols[3].text)

            if not venue_text or not start_text:
                continue

            key = (venue_text, start_text, entry_text, type_text)
            if key in seen:
                continue

            seen.add(key)
            games.append(make_game(venue_text, start_text, entry_text, type_text))
        except Exception:
            continue

    return games


def extract_games_from_body_text(driver):
    body_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [clean_text(line) for line in body_text.splitlines()]
    lines = [line for line in lines if line]

    games = []
    seen = set()

    pattern = re.compile(
        r"^(?P<venue>.+?)\s+"
        r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)\s+"
        r"(?P<entry>FREE|\$\s*\d+(?:\.\d{2})?)\s+"
        r"(?P<type>.+)$",
        re.IGNORECASE
    )

    for line in lines:
        upper_line = line.upper()

        if "TODAY'S LEAGUE EVENTS" in upper_line:
            continue
        if upper_line in {"VENUE", "START", "ENTRY", "TYPE"}:
            continue
        if upper_line == "VENUE START ENTRY TYPE":
            continue

        match = pattern.match(line)
        if not match:
            continue

        venue_text = match.group("venue")
        start_text = match.group("time")
        entry_text = match.group("entry")
        type_text = match.group("type")

        key = (venue_text, start_text, entry_text, type_text)
        if key in seen:
            continue

        seen.add(key)
        games.append(make_game(venue_text, start_text, entry_text, type_text))

    return games


def save_debug(driver):
    with open("npl_debug_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    with open("npl_debug_text.txt", "w", encoding="utf-8") as f:
        f.write(driver.find_element(By.TAG_NAME, "body").text)

    driver.save_screenshot("npl_debug_screenshot.png")


def scrape_npl():
    driver = setup_driver()

    try:
        driver.get(URL)
        time.sleep(10)

        click_text_if_found(driver, "ALL")
        click_text_if_found(driver, "NSW")
        click_text_if_found(driver, datetime.now().strftime("%a").upper())

        time.sleep(8)

        games = extract_games_from_rows(driver)

        if not games:
            games = extract_games_from_body_text(driver)

        save_debug(driver)

        return games
    finally:
        driver.quit()


def main():
    games = scrape_npl()

    with open("npl_games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Scraped {len(games)} NPL games")


if __name__ == "__main__":
    main()
