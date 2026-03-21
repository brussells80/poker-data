import requests
import json
import re
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean_text(value):
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_money(value):
    if value is None:
        return None

    text = clean_text(value)
    if not text:
        return None

    if text.upper() == "FREE":
        return 0

    match = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", text.replace(",", ""))
    if not match:
        return text

    number = match.group(1)
    try:
        return float(number) if "." in number else int(number)
    except Exception:
        return text


def extract_late_reg(description, starttime):
    description = (description or "").lower()
    late_reg = None

    patterns = [
        r'(\d{1,2}:\d{2})\s*pm?\s*late',
        r'late\s*reg(?:istration)?\s*(?:until)?\s*(\d{1,2}:\d{2})',
        r'(\d{1,2}:\d{2})\s*pm?\s*close'
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            late_reg = match.group(1)
            break

    if late_reg is None and starttime:
        try:
            start_dt = datetime.strptime(starttime, "%H:%M")
            late_reg = (start_dt + timedelta(hours=2, minutes=30)).strftime("%H:%M")
        except Exception:
            late_reg = None

    return late_reg


def pick_venue_name(tournament):
    return (
        clean_text(tournament.get("venue"))
        or clean_text(tournament.get("venuename"))
        or clean_text(tournament.get("venue_name"))
        or clean_text(tournament.get("location"))
        or clean_text(tournament.get("club"))
        or clean_text(tournament.get("idvenue"))
    )


def build_url():
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    future = today + timedelta(days=30)

    start = yesterday.strftime("%Y-%m-%d")
    end = future.strftime("%Y-%m-%d")

    # Use yesterday with date_g_ so today's tournaments are included.
    return (
        "https://api.kingspoker.com.au/api/v1/tournament/venue"
        f"?1=date_g_{start}"
        f"&2=date_le_{end}"
        "&exp=1*2"
        "&sort=date_asc:starttime_asc"
    )


def scrape_kings():
    url = build_url()
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tournaments = response.json()
    games = []
    seen = set()

    for tournament in tournaments:
        date_value = clean_text(tournament.get("date"))
        time_value = clean_text(tournament.get("starttime"))
        name_value = clean_text(tournament.get("title"))
        venue_value = pick_venue_name(tournament)
        buyin_value = parse_money(tournament.get("price"))
        guarantee_value = parse_money(tournament.get("gtd"))
        type_value = (
            clean_text(tournament.get("type"))
            or clean_text(tournament.get("description_type"))
            or None
        )

        late_reg = extract_late_reg(
            tournament.get("description", ""),
            time_value
        )

        game = {
            "league": "Kings",
            "name": name_value,
            "venue": venue_value,
            "date": date_value,
            "time": time_value,
            "buyin": buyin_value,
            "guarantee": guarantee_value,
            "late_reg": late_reg,
            "entries": None,
            "players_remaining": None,
            "type": type_value
        }

        dedupe_key = (
            game["name"],
            game["venue"],
            game["date"],
            game["time"],
            game["buyin"]
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        games.append(game)

    games.sort(key=lambda g: (g.get("date") or "", g.get("time") or "", g.get("name") or ""))

    with open("kings_games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(games)} Kings games")


if __name__ == "__main__":
    scrape_kings()
