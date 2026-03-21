import json
import os
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL = "https://www.npl.com.au/"


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def parse_buyin(entry_text):
    entry_text = clean_text(entry_text).upper()

    if not entry_text:
        return None

    if "FREE" in entry_text:
        return 0

    match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]{1,2})?)", entry_text)
    if match:
        value = match.group(1)
        try:
            if "." in value:
                return float(value)
            return int(value)
        except:
            return None

    return None


def parse_venue(venue_text):
    venue_text = clean_text(venue_text)

    distance = None
    distance_match = re.search(r"\(([\d\.]+)\s*KM\)", venue_text, re.IGNORECASE)
    if distance_match:
        try:
            distance = float(distance_match.group(1))
        except:
            distance = None
        venue_text = re.sub(r"\([\d\.]+\s*KM\)", "", venue_text, flags=re.IGNORECASE).strip()

    parts = [p.strip() for p in venue_text.split(",") if p.strip()]

    venue = parts[0].title() if len(parts) > 0 else ""
    suburb = parts[1].title() if len(parts) > 1 else ""
    state = parts[2].upper().split()[0] if len(parts) > 2 else ""

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
        "/snap/bin/chromium"
    ])

    chromedriver_path = get_existing_path([
        "/usr/bin/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
        "/usr/lib/chromium/chromedriver"
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
    options.add_argument("--window-size=1600,2200")

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def safe_click_by_text(driver, texts, timeout=5):
    for text in texts:
        xpaths = [
            f"//*[self::button or self::a or self::div or self::span][normalize-space()='{text}']",
            f"//*[contains(@class,'btn') and normalize-space()='{text}']",
            f"//*[contains(@class,'filter') and normalize-space()='{text}']",
            f"//*[contains(@class,'button') and normalize-space()='{text}']",
        ]

        for xpath in xpaths:
            try:
                elem = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1.0)
                return True
            except:
                pass

    return False


def current_day_labels():
    return [datetime.now().strftime("%a").upper()]


def wait_for_page_ready(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def extract_rows(driver):
    row_selectors = [
        "table tbody tr",
        "tbody tr",
        "table tr",
        ".table tbody tr",
        ".event-table tbody tr",
        ".events-table tbody tr",
    ]

    games = []
    seen = set()

    for selector in row_selectors:
        rows = driver.find_elements(By.CSS_SELECTOR, selector)

        for row in rows:
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
            except:
                continue

    return games


def save_debug_files(driver):
    try:
        with open("npl_debug_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except:
        pass

    try:
        driver.save_screenshot("npl_debug_screenshot.png")
    except:
        pass


def scrape_npl():
    driver = setup_driver()

    try:
        driver.get(URL)
        wait_for_page_ready(driver)
        time.sleep(5)

        safe_click_by_text(driver, ["ALL"])
        safe_click_by_text(driver, ["NSW"])
        safe_click_by_text(driver, current_day_labels())

        time.sleep(3)

        games = extract_rows(driver)

        if not games:
            save_debug_files(driver)

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
