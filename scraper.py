import requests
import json
import datetime
import re
from bs4 import BeautifulSoup

URL_TEMPLATE = "https://www.officeholidays.com/countries/malaysia/{year}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

ALL_STATES = [
    "Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan",
    "Pahang", "Perak", "Perlis", "Penang", "Sabah",
    "Sarawak", "Selangor", "Terengganu",
    "Kuala Lumpur", "Labuan", "Putrajaya"
]

TYPE_MAP = {
    "National Holiday": "National",
    "Regional Holiday": "Regional",
    "Government Holiday": "Government",
}


def parse_states_from_title(title):
    """Parse states from the title attribute of the country-listing link."""
    if not title or title == "Malaysia":
        return None
    states = [s.strip() for s in title.split(",")]
    return [s for s in states if s in ALL_STATES]


def parse_description(comments):
    """Return description only if it has info beyond state coverage, else None."""
    if not comments:
        return None

    lower = comments.lower()

    # Pure state-only phrases
    for phrase in ["most states", "several states", "some states"]:
        if lower == phrase:
            return None

    # Comments that only list state names + connectors (states now come from title)
    remaining = lower
    for state in ALL_STATES:
        remaining = remaining.replace(state.lower(), "")
    # Also remove common aliases
    for alias in ["malacca", "pulau pinang", "kdh", "ktn", "trg"]:
        remaining = remaining.replace(alias, "")
    remaining = re.sub(r'\b(only|and|except|excluding|all|regions?|states?)\b', '', remaining)
    remaining = remaining.strip(' ,.')
    if not remaining:
        return None

    return comments


def fetch(year=None):
    year = year or datetime.datetime.now(datetime.UTC).year
    url = URL_TEMPLATE.format(year=year)
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")
    rows = soup.select("table tr")[1:]

    seen = {}
    holidays = []

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue

        _, date_td, name_td, type_td, comments_td = tds[:5]

        # Get date from <time datetime="..."> attribute (more reliable than strptime)
        time_tag = date_td.find("time")
        if time_tag and time_tag.get("datetime"):
            iso_date = time_tag["datetime"]
        else:
            date_str = date_td.get_text(strip=True)
            try:
                dt = datetime.datetime.strptime(f"{date_str} {year}", "%b %d %Y")
                iso_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                iso_date = None

        name = name_td.get_text(strip=True)
        typ = type_td.get_text(strip=True)
        comments = comments_td.get_text(strip=True)

        simple_type = TYPE_MAP.get(typ)
        if simple_type is None:  # "Not A Public Holiday" or unknown
            continue

        # Get states from the title attribute on the link (tooltip data)
        a_tag = name_td.find("a", class_="country-listing")
        title = a_tag.get("title", "") if a_tag else ""
        states = parse_states_from_title(title)

        description = parse_description(comments)

        key = (iso_date, name)
        if key in seen:
            existing = seen[key]
            # Merge states from duplicate entries (same holiday split across rows)
            if existing.get("states") is None and states is not None:
                existing["states"] = states
            elif states is not None and existing.get("states") is not None:
                existing["states"] = sorted(set(existing["states"] + states))
            if description and not existing.get("description"):
                existing["description"] = description
            continue

        entry = {
            "date": iso_date,
            "holiday_name": name,
            "type": simple_type,
        }
        if simple_type != "National":
            entry["states"] = states
        if description is not None:
            entry["description"] = description

        seen[key] = entry
        holidays.append(entry)

    holidays.sort(key=lambda x: x["date"] or "")

    output = {
        "year": year,
        "source": "officeholidays.com",
        "holidays": holidays
    }

    out_file = f"malaysia_holidays_{year}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return out_file


if __name__ == "__main__":
    fetch()