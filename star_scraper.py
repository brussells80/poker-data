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
    """
    match = re.search(
        r"Blind Levels:\s*(\d+)\s*(?:minutes|minute|min)\b",
        detail_text,
        re.IGNORECASE
    )
    if match:
        return int(match.group(1))
    return None


def parse_late_reg_level(detail_text):
    """
    Example:
    Late Registration: Until start of level 7
    """
    match = re.search(
        r"Late Registration:\s*Until start of level\s*(\d+)",
        detail_text,
        re.IGNORECASE
    )
    if match:
        return int(match.group(1))
    return None


def calculate_late_reg(start_dt, blind_minutes, late_reg_level):
    """
    'Until start of level 7' means start time + 6 completed levels.
    """
    if not start_dt or not blind_minutes or not late_reg_level:
        return None

    offset_minutes = (late_reg_level - 1) * blind_minutes
    late_reg_dt = start_dt + timedelta(minutes=offset_minutes)
    return late_reg_dt.strftime("%H:%M")


def parse_detail_field(detail_text, label):
    pattern = rf"{re.escape(label)}:\s*(.+)"
    match = re.search(pattern, detail_text, re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return None


def normalize_venue(raw_venue, title):
    venue = clean_text(raw_venue)

    if venue:
        return venue

    title_clean = clean_text(title)
    for prefix in [
        "Star Sydney",
        "The Star Sydney",
        "Star Gold Coast",
        "The Star Gold Coast",
        "Star Brisbane",
        "The Star Brisbane",
        "Treasury Brisbane",
    ]:
        if title_clean.lower().startswith(prefix.lower()):
            return prefix.replace("Star ", "The Star ", 1) if prefix.startswith("Star ") else prefix

    return None


def build_game(title, start_dt, buyin, detail_text):
    venue = normalize_venue(parse_detail_field(detail_text, "Venue"), title)
    blind_minutes = parse_blind_level_minutes(detail_text)
    late_reg_level = parse_late_reg_level(detail_text)
    late_reg = calculate_late_reg(start_dt, blind_minutes, late_reg_level)

    reentry = parse_detail_field(detail_text, "Re-Entry")
    starting_stack = parse_detail_field(detail_text, "Starting Stack")

    game = {
        "league": "Star",
        "name": clean_text(title),
        "venue": venue,
        "suburb": None,
        "state": None,
        "date": start_dt.strftime("%Y-%m-%d") if start_dt else None,
        "time": format_time_24(start_dt),
        "buyin": buyin,
        "guarantee": None,
        "late_reg": late_reg,
        "entries": None,
        "players_remaining": None,
        "type": reentry,
        "blind_level_minutes": blind_minutes,
        "late_reg_level": late_reg_level,
        "starting_stack": starting_stack
    }

    if venue:
        venue_lower = venue.lower()
        if "sydney" in venue_lower:
            game["state"] = "NSW"
            game["suburb"] = "Sydney"
        elif "gold coast" in venue_lower:
            game["state"] = "QLD"
            game["suburb"] = "Gold Coast"
        elif "brisbane" in venue_lower or "treasury" in venue_lower:
            game["state"] = "QLD"
            game["suburb"] = "Brisbane"

    return game


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
            and line not in {"Tournament Schedule", "Submit", "TOURNAMENT NAME", "START DATE", "TOTAL BUY-IN", "Load more"}
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
        detail_end = min(i + 20, len(lines))
        detail_lines = []

        for j in range(detail_start, detail_end):
            candidate = lines[j]

            if j > detail_start:
                next_dt = parse_start_datetime(candidate)
                if next_dt:
                    break

            if candidate in {"Tournament conditions apply", "Prize pool can be found here", "Load more"}:
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
