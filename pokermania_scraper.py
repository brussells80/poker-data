import json
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


URL = "https://pokermania.com.au/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

DAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]
DAY_TO_INDEX = {day: i for i, day in enumerate(DAY_ORDER)}


VENUE_ALIASES = {
    "mollys tavern": "Molly Malone's Irish Tavern",
    "molly malones irish tavern": "Molly Malone's Irish Tavern",
    "molly malone's irish tavern": "Molly Malone's Irish Tavern",
    "molly malone’s irish tavern": "Molly Malone's Irish Tavern",
    "mollys tavern gts": "Molly Malone's Irish Tavern",
    "mollys tavern gt’s": "Molly Malone's Irish Tavern",
    "molly malone's irish tavern gts": "Molly Malone's Irish Tavern",
    "molly malone’s irish tavern gt’s": "Molly Malone's Irish Tavern",
}


SUBURB_ALIASES = {
    "surry hills": "Surry Hills",
    "taren point": "Taren Point",
    "cabramatta west": "Cabramatta West",
    "surryhills": "Surry Hills",
}


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def simplify_text(value):
    text = clean_text(value).lower()
    text = text.replace("’", "'")
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonicalize_venue(value):
    text = simplify_text(value)
    if not text:
        return ""

    if text in VENUE_ALIASES:
        return VENUE_ALIASES[text]

    return clean_text(value)


def canonicalize_suburb(value):
    text = simplify_text(value)
    if not text:
        return ""

    if text in SUBURB_ALIASES:
        return SUBURB_ALIASES[text]

    return clean_text(value).title()


def venue_match_score(summary_venue, detail_name, detail_title):
    s = simplify_text(summary_venue)
    d1 = simplify_text(detail_name)
    d2 = simplify_text(detail_title)

    canon_summary = simplify_text(canonicalize_venue(summary_venue))
    canon_d1 = simplify_text(canonicalize_venue(detail_name))
    canon_d2 = simplify_text(canonicalize_venue(detail_title))

    scores = []

    for a in [s, canon_summary]:
        for b in [d1, d2, canon_d1, canon_d2]:
            if not a or not b:
                continue
            if a == b:
                scores.append(100)
            elif a in b or b in a:
                scores.append(80)
            else:
                a_words = set(a.split())
                b_words = set(b.split())
                overlap = len(a_words & b_words)
                if overlap:
                    scores.append(overlap * 10)

    return max(scores) if scores else 0


def parse_money(value):
    text = clean_text(value)
    if not text:
        return None

    if text.upper() == "FREE":
        return 0

    match = re.search(r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", text)
    if not match:
        return None

    number = match.group(1).replace(",", "")
    try:
        return float(number) if "." in number else int(number)
    except Exception:
        return None


def normalize_time(text):
    text = clean_text(text).upper().replace(".", ":")

    range_match = re.match(r"^(.+?)(?:\s*[–-]\s*.+)?$", text)
    if range_match:
        text = range_match.group(1).strip()

    text = re.sub(r"(\d)\.(\d{2})", r"\1:\2", text)

    for fmt in ("%I:%M %p", "%I %p"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            continue

    return None


def infer_type_from_prize(prize_text, notes_text):
    prize = clean_text(prize_text).lower()
    notes = clean_text(notes_text).lower()

    if "cash game" in prize or "cash game" in notes:
        return "Cash Game"
    if "freezeout" in notes:
        return "Freezeout"
    if "tournament" in prize:
        return "Tournament"
    return None


def extract_guarantee(prize_text):
    prize = clean_text(prize_text)
    if "gtd" in prize.lower():
        return parse_money(prize)
    if "exp" in prize.lower():
        return parse_money(prize)
    return None


def extract_buyin_range(entry_fee_text):
    text = clean_text(entry_fee_text)
    if not text:
        return None

    if "-" in text or "–" in text:
        parts = re.split(r"\s*[–-]\s*", text)
        values = [parse_money(p) for p in parts if parse_money(p) is not None]
        if len(values) == 2:
            return {
                "min": values[0],
                "max": values[1]
            }

    value = parse_money(text)
    return value


def day_to_next_date(day_name):
    today = datetime.today()
    target_idx = DAY_TO_INDEX[day_name]
    current_idx = today.weekday()
    days_ahead = (target_idx - current_idx) % 7
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime("%Y-%m-%d")


def parse_summary_rows(lines):
    games = []

    i = 0
    while i < len(lines):
        line = clean_text(lines[i])

        if line not in DAY_ORDER:
            i += 1
            continue

        day_name = line

        parts = [day_name]
        j = i + 1
        while j < len(lines):
            candidate = clean_text(lines[j])
            if candidate == "More Details":
                break
            if candidate in DAY_ORDER:
                break
            parts.append(candidate)
            j += 1

        summary_text = " ".join(parts)

        time_match = re.search(r"(\d{1,2}\.\d{2}\s*[AP]M)", summary_text, re.IGNORECASE)
        if not time_match:
            i = j + 1 if j < len(lines) and lines[j] == "More Details" else j
            continue

        raw_time = time_match.group(1)
        left = clean_text(summary_text[:time_match.start()])
        right = clean_text(summary_text[time_match.end():])

        entry_fee = right if right else None

        left = re.sub(rf"^{day_name}\s+", "", left, flags=re.IGNORECASE).strip()

        prize = None
        venue = None
        suburb = None

        if left.lower().startswith("cash game"):
            prize = "Cash Game"
            rest = left[9:].strip()
            rest_tokens = rest.split()

            if len(rest_tokens) >= 3:
                suburb = " ".join(rest_tokens[-2:])
                venue = " ".join(rest_tokens[:-2])

                if simplify_text(suburb) not in {"surry hills", "taren point", "cabramatta west"}:
                    suburb = rest_tokens[-1]
                    venue = " ".join(rest_tokens[:-1])
            else:
                venue = rest
        else:
            prize_match = re.match(r"^(\$\s*[0-9,]+\s*(?:EXP|GTD)?|Tournament)\s+(.+)$", left, re.IGNORECASE)
            if prize_match:
                prize = clean_text(prize_match.group(1))
                rest = clean_text(prize_match.group(2))
            else:
                rest = left

            rest_tokens = rest.split()
            if len(rest_tokens) >= 3:
                suburb = " ".join(rest_tokens[-2:])
                venue = " ".join(rest_tokens[:-2])

                if simplify_text(suburb) not in {"surry hills", "taren point", "cabramatta west"}:
                    suburb = rest_tokens[-1]
                    venue = " ".join(rest_tokens[:-1])
            else:
                venue = rest

        games.append({
            "day": day_name,
            "summary_prize": clean_text(prize) if prize else None,
            "venue": canonicalize_venue(venue),
            "suburb": canonicalize_suburb(suburb),
            "summary_time": normalize_time(raw_time),
            "summary_entry_fee": clean_text(entry_fee)
        })

        i = j + 1 if j < len(lines) and clean_text(lines[j]) == "More Details" else j

    return games


def parse_detail_sections(lines):
    details = []
    i = 0

    while i < len(lines):
        line = clean_text(lines[i])

        if not line.startswith("### "):
            i += 1
            continue

        section_name = clean_text(line.replace("### ", "", 1))
        display_title = section_name

        j = i + 1
        if j < len(lines) and clean_text(lines[j]).startswith("# "):
            display_title = clean_text(lines[j].replace("# ", "", 1))
            j += 1

        block = []
        while j < len(lines):
            candidate = clean_text(lines[j])
            if candidate.startswith("### "):
                break
            block.append(candidate)
            j += 1

        block_text = "\n".join(block)

        def field_value(label):
            pattern = rf"{re.escape(label)}\s*:\s*(.+)"
            match = re.search(pattern, block_text, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))
            return None

        venue_address = field_value("Venue Address")
        venue_contact = field_value("Venue Contact")
        when = field_value("When")
        start_time = field_value("Start Time")
        late_entry = field_value("Late Entry")
        entry_fee = field_value("Entry Fee")
        starting_stack = field_value("Starting Stack")
        prize = field_value("Prize")
        additional_notes = field_value("Additional Notes")

        website = None
        website_match = re.search(
            r"Venue Website\s*:\s*(https?://[^\s]+|[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s]*)",
            block_text,
            re.IGNORECASE
        )
        if website_match:
            website = clean_text(website_match.group(1))

        details.append({
            "section_name": canonicalize_venue(section_name),
            "display_title": canonicalize_venue(display_title),
            "when": when,
            "start_time": normalize_time(start_time),
            "late_entry": normalize_time(late_entry),
            "entry_fee_raw": entry_fee,
            "starting_stack": starting_stack,
            "prize_raw": prize,
            "additional_notes": additional_notes,
            "venue_address": venue_address,
            "venue_contact": venue_contact,
            "venue_website": website
        })

        i = j

    return details


def merge_summary_and_details(summary_rows, detail_sections):
    games = []
    used_detail_indexes = set()

    for summary in summary_rows:
        best_idx = None
        best_score = 0

        for idx, detail in enumerate(detail_sections):
            if idx in used_detail_indexes:
                continue

            if clean_text(detail["when"]).lower() != clean_text(summary["day"]).lower():
                continue

            score = venue_match_score(
                summary["venue"],
                detail["section_name"],
                detail["display_title"]
            )

            if score > best_score:
                best_score = score
                best_idx = idx

        detail = detail_sections[best_idx] if best_idx is not None and best_score >= 40 else {}
        if best_idx is not None and best_score >= 40:
            used_detail_indexes.add(best_idx)

        prize_text = detail.get("prize_raw") or summary.get("summary_prize") or ""
        notes_text = detail.get("additional_notes") or ""
        entry_fee_raw = detail.get("entry_fee_raw") or summary.get("summary_entry_fee")

        venue = canonicalize_venue(detail.get("display_title") or summary.get("venue"))
        suburb = canonicalize_suburb(summary.get("suburb"))
        state = "NSW"

        game_type = infer_type_from_prize(prize_text, notes_text)
        guarantee = extract_guarantee(prize_text)

        if game_type == "Cash Game":
            name = f"{venue} {summary['day']} Cash Game"
        else:
            name = f"{venue} {summary['day']}"

        game = {
            "league": "PokerMania",
            "name": clean_text(name),
            "venue": venue,
            "suburb": suburb,
            "state": state,
            "date": day_to_next_date(summary["day"]),
            "time": detail.get("start_time") or summary.get("summary_time"),
            "buyin": extract_buyin_range(entry_fee_raw),
            "guarantee": guarantee,
            "late_reg": detail.get("late_entry"),
            "entries": None,
            "players_remaining": None,
            "type": game_type,
            "starting_stack": detail.get("starting_stack"),
            "venue_address": detail.get("venue_address"),
            "venue_contact": detail.get("venue_contact"),
            "venue_website": detail.get("venue_website"),
            "additional_notes": notes_text or None
        }

        games.append(game)

    return games


def scrape_pokermania():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text("\n")

    lines = [clean_text(line) for line in page_text.splitlines()]
    lines = [line for line in lines if line]

    summary_rows = parse_summary_rows(lines)
    detail_sections = parse_detail_sections(lines)
    games = merge_summary_and_details(summary_rows, detail_sections)

    games.sort(key=lambda g: (g.get("date") or "", g.get("time") or "", g.get("name") or ""))

    with open("pokermania_games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(games)} PokerMania games")


if __name__ == "__main__":
    scrape_pokermania()
