import json
import os
import re
import time
from datetime import datetime, timedelta

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


def make_game(venue_text, start_text, entry_text, type_text, game_date):
    venue, suburb, state, distance = parse_venue(venue_text)

    return {
        "league": "NPL",
        "state": state,
        "name": f"{venue} {clean_text(start_text)}".strip(),
        "venue": venue,
        "suburb": suburb,
        "date": game_date,
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


def click_exact_text(driver, text):
    xpaths = [
        f"//*[self::button or self::a or self::div or self::span][normalize-space()='{text}']",
        f"//*[contains(@class,'btn') and normalize-space()='{text}']",
        f"//*[contains(@class,'filter') and normalize-space()='{text}']",
    ]

    for xpath in xpaths:
        elems = driver.find_elements(By.XPATH, xpath)
        for elem in elems:
            try:
                if not elem.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1.5)
                return True
            except Exception:
                continue

    return False


def get_next_7_days():
    today = datetime.now()
    result = []

    for offset in range(7):
        target_date = today + timedelta(days=offset)
        result.append({
            "day_label": target_date.strftime("%a").upper(),
            "date": target_date.strftime("%Y-%m-%d"),
            "debug_suffix": f"{offset}_{target_date.strftime('%a').lower()}"
        })

    return result


def extract_games_from_table_rows(driver, game_date):
    games = []
    seen = set()

    rows = driver.find_elements(By.XPATH, "//tr")

    for row in rows:
        try:
            cells = row.find_elements(By.XPATH, ".//*[self::td or self::th]")
            texts = [clean_text(c.text) for c in cells if clean_text(c.text)]

            if len(texts) < 4:
                continue
            if texts[0].upper() == "VENUE":
                continue

            venue_text = texts[0]
            start_text = texts[1]
            entry_text = texts[2]
            type_text = texts[3]

            if not re.search(r"\d{1,2}:\d{2}\s*[AP]M", start_text, re.IGNORECASE):
                continue

            key = (venue_text, start_text, entry_text, type_text)
            if key in seen:
                continue

            seen.add(key)
            games.append(make_game(venue_text, start_text, entry_text, type_text, game_date))
        except Exception:
            continue

    return games


def extract_games_from_body_text(driver, game_date):
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
        games.append(make_game(venue_text, start_text, entry_text, type_text, game_date))

    return games


def extract_games_for_current_view(driver, game_date):
    games = extract_games_from_table_rows(driver, game_date)
    if not games:
        games = extract_games_from_body_text(driver, game_date)
    return games


def save_debug_files(driver, suffix=""):
    suffix_part = f"_{suffix}" if suffix else ""

    with open(f"npl_debug_source{suffix_part}.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    with open(f"npl_debug_text{suffix_part}.txt", "w", encoding="utf-8") as f:
        f.write(driver.find_element(By.TAG_NAME, "body").text)

    driver.save_screenshot(f"npl_debug_screenshot{suffix_part}.png")


def find_heading_y(driver):
    elems = driver.find_elements(
        By.XPATH,
        "//*[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), \"TODAY'S LEAGUE EVENTS\")]"
    )
    for elem in elems:
        try:
            if elem.is_displayed():
                return elem.location.get("y", 0)
        except Exception:
            continue
    return 0


def find_day_container(driver, day_label):
    heading_y = find_heading_y(driver)

    candidates = driver.find_elements(By.XPATH, "//*")
    matches = []

    for elem in candidates:
        try:
            if not elem.is_displayed():
                continue

            text = clean_text(elem.text).upper()
            if text != day_label:
                continue

            x = elem.location.get("x", 0)
            y = elem.location.get("y", 0)
            width = elem.size.get("width", 0)
            height = elem.size.get("height", 0)

            if y < heading_y:
                continue
            if y > heading_y + 250:
                continue
            if width > 150 or height > 100:
                continue

            # Prefer clickable parent/container rather than the raw text node
            clickable = elem
            for _ in range(4):
                parent = clickable.find_element(By.XPATH, "..")
                parent_tag = parent.tag_name.lower()
                parent_text = clean_text(parent.text).upper()

                if (
                    parent_tag in {"a", "button"}
                    or "btn" in (parent.get_attribute("class") or "").lower()
                    or "filter" in (parent.get_attribute("class") or "").lower()
                    or day_label in parent_text
                ):
                    clickable = parent
                else:
                    break

            matches.append((y, x, clickable))
        except Exception:
            continue

    matches.sort(key=lambda item: (item[0], item[1]))
    return matches[0][2] if matches else None


def click_day_tab(driver, day_label):
    elem = find_day_container(driver, day_label)
    if elem is None:
        return False

    try:
        before = driver.find_element(By.TAG_NAME, "body").text
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", elem)
        time.sleep(4)
        after = driver.find_element(By.TAG_NAME, "body").text

        print(f"Clicked {day_label}. Body changed: {before != after}")
        return True
    except Exception:
        return False


def scrape_npl():
    driver = setup_driver()

    try:
        driver.get(URL)
        time.sleep(10)

        click_exact_text(driver, "ALL")
        time.sleep(1)

        click_exact_text(driver, "NSW")
        time.sleep(2)

        all_games = []
        seen = set()
        next_7_days = get_next_7_days()

        for i, day_info in enumerate(next_7_days):
            day_label = day_info["day_label"]
            game_date = day_info["date"]
            debug_suffix = day_info["debug_suffix"]

            if i == 0:
                print(f"Using initial page view for {day_label} ({game_date})")
            else:
                clicked = click_day_tab(driver, day_label)
                if not clicked:
                    print(f"Could not click day tab: {day_label}")
                    save_debug_files(driver, f"failed_{debug_suffix}")
                    continue

            time.sleep(3)

            day_games = extract_games_for_current_view(driver, game_date)
            print(f"Scraped {len(day_games)} games for {day_label} ({game_date})")

            save_debug_files(driver, debug_suffix)

            for game in day_games:
                key = (
                    game["venue"],
                    game["suburb"],
                    game["date"],
                    game["time"],
                    game["buyin"],
                    game["type"]
                )
                if key not in seen:
                    seen.add(key)
                    all_games.append(game)

        return all_games

    finally:
        driver.quit()


def main():
    games = scrape_npl()

    with open("npl_games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Scraped {len(games)} total NPL games")


if __name__ == "__main__":
    main()
