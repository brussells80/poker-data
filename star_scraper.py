import json
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


URL = "https://www.starpoker.com.au/tournaments"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_money(value):
    text = clean_text(value)

    if not text:
        return None

    match = re.search(r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", text)
    if not match:
        return None

    number = match.group(1).replace(",", "")
    try:
        return float(number) if "." in number else int(number)
    except Exception:
        return None


def parse_start_datetime(text):
    """
    Example:
    Fri, 20 Mar 2026 6:30pm
    """
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
    """
    Examples:
    Blind Levels: 20 minutes
    Blind Levels: 30 minutes for Day 1 (16 levels) and then 45 min...
    Blind levels 15 mins
    """
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
    """
    Tries to capture many variants, e.g.:
    - Late Registration: Until start of level 7
    - Late Registration Closes: Start of level 7
    - Late Reg: start of level 9
    - Late Registration closes at the start of level 12
    """
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
    """
    'Until start of level 7' means late reg closes when level 7 starts,
    so add 6 blind levels to the start time.
    """
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


def scrape_star():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text("\n")

    lines = [clean_text(line) for line in page_text.splitlines()]
    lines = [line for line in lines if line]

    games = []
    seen = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        looks_like_title = (
            not line.lower().startswith("choose ")
            and line not in {
                "Tournament Schedule",
                "Submit",
                "TOURNAMENT NAME",
                "START DATE",
                "TOTAL BUY-IN",
                "Load more"
            }
            and i + 3 < len(lines)
        )

        if not looks_like_title:
            i += 1
            continue

        title = lines[i]
        date_line = lines[i + 1]
        buyin_line = lines[i + 2]

        start_dt = parse_start_datetime(date_line)
        buyin = parse_money(buyin_line)

        if not start_dt or buyin is None:
            i += 1
            continue

        detail_start = i + 3
        detail_end = min(i + 30, len(lines))
        detail_lines = []

        for j in range(detail_start, detail_end):
            candidate = lines[j]

            if j > detail_start:
                maybe_next_dt = parse_start_datetime(candidate)
                if maybe_next_dt:
                    break

            if candidate in {
                "Tournament conditions apply",
                "Prize pool can be found here",
                "Load more"
            }:
                continue

            detail_lines.append(candidate)

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

        i += 1

    games.sort(key=lambda g: (g.get("date") or "", g.get("time") or "", g.get("name") or ""))

    with open("star_games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(games)} Star games")


if __name__ == "__main__":
    scrape_star()
