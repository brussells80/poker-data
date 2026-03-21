import json
import os
import re
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.starpoker.com.au/tournaments"


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_money(value):
    text = clean_text(value)

    if not text:
        return None

    match = re.search(r"\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", text)
    if not match:
        return None

    number = match.group(1).replace(",", "")
    try:
        return float(number) if "." in number else int(number)
    except Exception:
        return None


def is_date_line(text):
    text = clean_text(text)
    return bool(re.match(r"^[A-Z][a-z]{2}, \d{1,2} [A-Z][a-z]{2} \d{4} \d{1,2}:\d{2}(am|pm)$", text))


def parse_start_datetime(text):
    text = clean_text(text)

    for fmt in ("%a, %d %b %Y %I:%M%p", "%a, %d %b %Y %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def format_time_24(dt):
    return dt.strftime("%H:%M") if dt else None


def parse_blind_level_minutes(detail_text):
    patterns = [
        r"Blind Levels?\s*:\s*(\d+)\s*(?:minutes|minute|min|mins)\b",
        r"Blind Levels?\s*(\d+)\s*(?:minutes|minute|min|mins)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, detail_text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def parse_late_reg_level(detail_text):
    patterns = [
        r"Late Registration(?: Closes)?\s*:\s*Until start of level\s*(\d+)",
        r"Late Registration(?: Closes)?\s*:\s*Start of level\s*(\d+)",
        r"Late Registration(?: Closes)?\s*:\s*At the start of level\s*(\d+)",
        r"Late Registration(?: Closes)?\s*:\s*Closes at the start of level\s*(\d+)",
        r"Late Reg(?:istration)?\s*:\s*Until start of level\s*(\d+)",
        r"Late Reg(?:istration)?\s*:\s*Start of level\s*(\d+)",
        r"Late Reg(?:istration)?\s*:\s*At the start of level\s*(\d+)",
        r"Late Reg(?:istration)?\s*closes?\s*at\s*the\s*start\s*of\s*level\s*(\d+)",
        r"Late Registration(?: Closes)?\s*.*?start of level\s*(\d+)",
        r"Late Reg(?:istration)?\s*.*?start of level\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, detail_text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                continue

    return None


def calculate_late_reg(start_dt, blind_minutes, late_reg_level):
    if not start_dt or not blind_minutes or not late_reg_level:
        return None

    if late_reg_level < 1:
        return None

    offset_minutes = (late_reg_level - 1) * blind_minutes
    late_reg_dt = start_dt + timedelta(minutes=offset_minutes)
    return late_reg_dt.strftime("%H:%M")


def parse_detail_field(detail_text, label):
    pattern = rf"{re.escape(label)}\s*:\s*(.+)"
    match = re.search(pattern, detail_text, re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return None


def normalize_venue(raw_venue, title):
    venue = clean_text(raw_venue)

    if venue:
        return venue

    title_clean = clean_text(title)

    venue_prefixes = [
        "The Star Sydney",
        "The Star Gold Coast",
        "The Star Brisbane",
        "Treasury Brisbane",
        "Star Sydney",
        "Star Gold Coast",
        "Star Brisbane",
    ]

    for prefix in venue_prefixes:
        if title_clean.lower().startswith(prefix.lower()):
            if prefix.startswith("Star "):
                return prefix.replace("Star ", "The Star ", 1)
            return prefix

    return None


def infer_state_and_suburb(venue):
    if not venue:
        return None, None

    venue_lower = venue.lower()

    if "sydney" in venue_lower:
        return "NSW", "Sydney"

    if "gold coast" in venue_lower:
        return "QLD", "Gold Coast"

    if "brisbane" in venue_lower or "treasury" in venue_lower:
        return "QLD", "Brisbane"

    return None, None


def build_game(title, start_dt, buyin, detail_text):
    venue = normalize_venue(parse_detail_field(detail_text, "Venue"), title)
    state, suburb = infer_state_and_suburb(venue)

    blind_minutes = parse_blind_level_minutes(detail_text)
    late_reg_level = parse_late_reg_level(detail_text)
    late_reg = calculate_late_reg(start_dt, blind_minutes, late_reg_level)

    reentry = (
        parse_detail_field(detail_text, "Re-Entry")
        or parse_detail_field(detail_text, "Re Entry")
        or parse_detail_field(detail_text, "Reentries")
    )

    starting_stack = parse_detail_field(detail_text, "Starting Stack")

    guarantee = (
        parse_money(parse_detail_field(detail_text, "Guarantee"))
        or parse_money(parse_detail_field(detail_text, "Guaranteed Prize Pool"))
        or parse_money(parse_detail_field(detail_text, "Prize Pool"))
    )

    return {
        "league": "Star",
        "name": clean_text(title),
        "venue": venue,
        "suburb": suburb,
        "state": state,
        "date": start_dt.strftime("%Y-%m-%d") if start_dt else None,
        "time": format_time_24(start_dt),
        "buyin": buyin,
        "guarantee": guarantee,
        "late_reg": late_reg,
        "entries": None,
        "players_remaining": None,
        "type": reentry,
        "blind_level_minutes": blind_minutes,
        "late_reg_level": late_reg_level,
        "starting_stack": starting_stack
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
    options.add_argument("--window-size=1800,4000")

    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)


def click_load_more_until_done(driver, max_clicks=40):
    clicks = 0

    while clicks < max_clicks:
        found_button = None

        candidates = driver.find_elements(
            By.XPATH,
            "//*[self::a or self::button or self::div or self::span][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]"
        )

        for elem in candidates:
            try:
                if not elem.is_displayed():
                    continue
                found_button = elem
                break
            except Exception:
                continue

        if not found_button:
            print("No more Load more button found")
            break

        before_height = driver.execute_script("return document.body.scrollHeight")
        before_text = driver.find_element(By.TAG_NAME, "body").text

        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", found_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", found_button)
            time.sleep(3)
        except Exception:
            try:
                found_button.click()
                time.sleep(3)
            except Exception:
                print("Could not click Load more")
                break

        after_height = driver.execute_script("return document.body.scrollHeight")
        after_text = driver.find_element(By.TAG_NAME, "body").text

        clicks += 1
        print(f"Clicked Load more {clicks} time(s)")

        if before_height == after_height and before_text == after_text:
            print("Page content did not change after click")
            break


def extract_games_from_lines(lines):
    games = []
    seen = set()

    skip_lines = {
        "Tournament Schedule",
        "Submit",
        "TOURNAMENT NAME",
        "START DATE",
        "TOTAL BUY-IN",
        "Load more",
        "Tournament conditions apply",
        "Prize pool can be found here",
    }

    i = 0
    while i < len(lines):
        line = lines[i]

        if line in skip_lines or line.lower().startswith("choose "):
            i += 1
            continue

        if not is_date_line(line):
            i += 1
            continue

        date_line = line
        start_dt = parse_start_datetime(date_line)

        if not start_dt:
            i += 1
            continue

        # Title is all contiguous lines immediately before the date line,
        # stopping when we hit a previous buyin/date/header/control line.
        title_parts = []
        j = i - 1

        while j >= 0:
            prev_line = lines[j]

            if (
                prev_line in skip_lines
                or prev_line.lower().startswith("choose ")
                or is_date_line(prev_line)
                or parse_money(prev_line) is not None and prev_line.strip().startswith("$")
            ):
                break

            title_parts.insert(0, prev_line)
            j -= 1

        title = clean_text(" ".join(title_parts))

        # Next line after date should be buyin
        buyin = None
        buyin_index = i + 1
        if buyin_index < len(lines):
            buyin = parse_money(lines[buyin_index])

        if not title or buyin is None:
            i += 1
            continue

        detail_lines = []
        k = i + 2

        while k < len(lines):
            candidate = lines[k]

            if is_date_line(candidate):
                break

            # Stop if this looks like next event title followed by a date soon after
            if k + 1 < len(lines) and is_date_line(lines[k + 1]):
                break

            if candidate not in skip_lines:
                detail_lines.append(candidate)

            k += 1

        detail_text = "\n".join(detail_lines)
        game = build_game(title, start_dt, buyin, detail_text)

        dedupe_key = (
            game["name"],
            game["venue"],
            game["date"],
            game["time"],
            game["buyin"]
        )

        if dedupe_key not in seen:
            seen.add(dedupe_key)
            games.append(game)

        i = k

    return games


def scrape_star():
    driver = setup_driver()

    try:
        driver.get(URL)
        time.sleep(8)

        click_load_more_until_done(driver)

        html = driver.page_source

        with open("star_debug_source.html", "w", encoding="utf-8") as f:
            f.write(html)

        driver.save_screenshot("star_debug_screenshot.png")

    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text("\n")

    lines = [clean_text(line) for line in page_text.splitlines()]
    lines = [line for line in lines if line]

    games = extract_games_from_lines(lines)
    games.sort(key=lambda g: (g.get("date") or "", g.get("time") or "", g.get("name") or ""))

    with open("star_games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(games)} Star games")


if __name__ == "__main__":
    scrape_star()
