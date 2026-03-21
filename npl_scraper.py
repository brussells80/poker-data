import json
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
    """
    Example:
    BERKELEY SPORTS CLUB, WOLLONGONG, NSW
    CONCOURSE BAR, SYDNEY CBD, NSW (3.2 KM)
    """
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
    state = ""

    if len(parts) > 2:
        state = parts[2].upper().split()[0]

    return venue, suburb, state, distance


def make_game(venue_text, start_text, entry_text, type_text):
    venue, suburb, state, distance = parse_venue(venue_text)

    today = datetime.now().strftime("%Y-%m-%d")

    name_parts = [venue]
    if start_text:
        name_parts.append(start_text)

    return {
        "league": "NPL",
        "state": state,
        "name": " ".join(name_parts).strip(),
        "venue": venue,
        "suburb": suburb,
        "date": today,
        "time": clean_text(start_text),
        "buyin": parse_buyin(entry_text),
        "guarantee": None,
        "late_reg": None,
        "type": clean_text(type_text),
        "distance_km": distance,
        "lat": None,
        "lng": None
    }


def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1600,2200")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def safe_click_by_text(driver, texts, timeout=5):
    """
    Tries to click a button/filter matching any visible text in `texts`.
    """
    for text in texts:
        xpath_candidates = [
            f"//*[self::button or self::a or self::div or self::span][normalize-space()='{text}']",
            f"//*[contains(@class,'btn') and normalize-space()='{text}']",
            f"//*[contains(@class,'filter') and normalize-space()='{text}']",
        ]

        for xpath in xpath_candidates:
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
    day = datetime.now().strftime("%a").upper()  # MON, TUE, WED...
    return [day]


def wait_for_page_ready(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def extract_rows_from_tables(driver):
    games = []

    # Try all possible row patterns
    row_selectors = [
        "table tbody tr",
        "tbody tr",
        "table tr",
        ".table tbody tr",
        ".event-table tbody tr",
        ".events-table tbody tr",
    ]

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


def extract_rows_from_text_blocks(driver):
    """
    Fallback parser if table markup is unusual but visible text exists.
    """
    games = []

    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            text = clean_text(table.text)
            if "VENUE" not in text.upper() or "START" not in text.upper():
                continue

            rows = table.find_elements(By.XPATH, ".//tr")
            for row in rows:
                cols = row.find_elements(By.XPATH, ".//td")
                if len(cols) < 4:
                    continue

                venue_text = clean_text(cols[0].text)
                start_text = clean_text(cols[1].text)
                entry_text = clean_text(cols[2].text)
                type_text = clean_text(cols[3].text)

                if venue_text and start_text:
                    games.append(make_game(venue_text, start_text, entry_text, type_text))
    except:
        pass

    deduped = []
    seen = set()
    for g in games:
        key = (g["venue"], g["time"], g["buyin"], g["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(g)

    return deduped


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

        # Try to set useful filters if present
        safe_click_by_text(driver, ["ALL"])
        safe_click_by_text(driver, ["NSW"])
        safe_click_by_text(driver, current_day_labels())

        time.sleep(3)

        games = extract_rows_from_tables(driver)

        if not games:
            games = extract_rows_from_text_blocks(driver)

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
