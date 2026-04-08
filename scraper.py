import hashlib
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


def export_ics(year=None, states=None):
    """Export holidays as an ICS calendar file.

    Args:
        year: Year to export. Defaults to current year.
        states: Optional list of state names to filter by. If None, exports all holidays.
    """
    year = year or datetime.datetime.now(datetime.UTC).year
    json_file = f"malaysia_holidays_{year}.json"
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    holidays = data["holidays"]
    if states:
        states_set = set(states)
        holidays = [
            h for h in holidays
            if h["type"] == "National" or (h.get("states") and states_set & set(h["states"]))
        ]

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Malaysia Holidays//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for h in holidays:
        date_str = h["date"]
        if not date_str:
            continue
        date_val = datetime.date.fromisoformat(date_str)
        next_day = date_val + datetime.timedelta(days=1)

        description = h["type"]
        if h.get("states"):
            description += f" — {', '.join(h['states'])}"
        if h.get("description"):
            description += f" — {h['description']}"

        uid = f"malaysia-holidays-{year}-{date_str}-{hashlib.md5(h['holiday_name'].encode()).hexdigest()[:8]}"

        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART;VALUE=DATE:{date_str.replace('-', '')}",
            f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
            f"SUMMARY:{h['holiday_name']}",
            f"DESCRIPTION:{description}",
            f"UID:{uid}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    suffix = f"_{'-'.join(states)}" if states else ""
    out_file = f"malaysia_holidays_{year}{suffix}.ics"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(f"ICS exported to {out_file}")
    return out_file


FRI_SAT_STATES = {"Kedah", "Kelantan", "Terengganu"}
SAT_SUN_STATES = set(ALL_STATES) - FRI_SAT_STATES


def long_weekends(year=None):
    """Detect long weekends (holidays adjacent to Sat-Sun or Fri-Sat weekends).

    Returns two lists: one for Sat-Sun states, one for Fri-Sat states.
    Each long weekend is a dict with start_date, end_date, length_days, holiday_name, states.
    """
    year = year or datetime.datetime.now(datetime.UTC).year
    json_file = f"malaysia_holidays_{year}.json"
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    holiday_dates = {}
    for h in data["holidays"]:
        if not h["date"]:
            continue
        d = datetime.date.fromisoformat(h["date"])
        holiday_dates[d] = h

    results_sat_sun = []
    results_fri_sat = []

    def is_holiday(d):
        return d in holiday_dates

    def holiday_states(d):
        h = holiday_dates.get(d)
        if not h:
            return None
        if h["type"] == "National":
            return ALL_STATES
        return h.get("states")

    for date_val in sorted(holiday_dates.keys()):
        h = holiday_dates[date_val]
        weekday = date_val.weekday()  # Mon=0, Sun=6

        # --- Sat-Sun states logic ---
        if weekday == 0:  # Monday
            # Sat-Mon 3-day weekend
            results_sat_sun.append({
                "start_date": (date_val - datetime.timedelta(days=2)).isoformat(),
                "end_date": date_val.isoformat(),
                "length_days": 3,
                "holiday_name": h["holiday_name"],
                "states": holiday_states(date_val),
            })
        elif weekday == 4:  # Friday
            # Fri-Sun 3-day weekend
            results_sat_sun.append({
                "start_date": date_val.isoformat(),
                "end_date": (date_val + datetime.timedelta(days=2)).isoformat(),
                "length_days": 3,
                "holiday_name": h["holiday_name"],
                "states": holiday_states(date_val),
            })
        elif weekday == 5:  # Saturday
            # Sat-Sun weekend already, check if Sunday is also a holiday for 3-day
            sun = date_val + datetime.timedelta(days=1)
            if is_holiday(sun):
                # Sat-Mon (if Monday also holiday)
                mon = date_val + datetime.timedelta(days=2)
                if is_holiday(mon):
                    results_sat_sun.append({
                        "start_date": date_val.isoformat(),
                        "end_date": mon.isoformat(),
                        "length_days": 3,
                        "holiday_name": f"{h['holiday_name']} + {holiday_dates[sun]['holiday_name']} + {holiday_dates[mon]['holiday_name']}",
                        "states": holiday_states(date_val),
                    })
        elif weekday == 6:  # Sunday
            # Sun itself is a holiday — check if Monday is also for a 2+ day extension
            mon = date_val + datetime.timedelta(days=1)
            if is_holiday(mon):
                results_sat_sun.append({
                    "start_date": (date_val - datetime.timedelta(days=1)).isoformat(),
                    "end_date": mon.isoformat(),
                    "length_days": 3,
                    "holiday_name": f"{h['holiday_name']} + {holiday_dates[mon]['holiday_name']}",
                    "states": holiday_states(date_val),
                })

        # --- Fri-Sat states logic ---
        if weekday == 6:  # Sunday
            # Fri-Sat-Sun: Sun is the "Friday" equivalent for Fri-Sat states
            # Actually for Fri-Sat: weekend is Fri+Sat, so Sunday holiday adjacent to Sat
            # Sun alone after Sat = 3-day (Fri-Sun)
            results_fri_sat.append({
                "start_date": (date_val - datetime.timedelta(days=2)).isoformat(),
                "end_date": date_val.isoformat(),
                "length_days": 3,
                "holiday_name": h["holiday_name"],
                "states": holiday_states(date_val),
            })
        elif weekday == 3:  # Thursday
            # Thu-Sat: 3-day weekend for Fri-Sat states
            results_fri_sat.append({
                "start_date": date_val.isoformat(),
                "end_date": (date_val + datetime.timedelta(days=2)).isoformat(),
                "length_days": 3,
                "holiday_name": h["holiday_name"],
                "states": holiday_states(date_val),
            })
        elif weekday == 4:  # Friday
            # Friday is weekend day for Fri-Sat states — if Thu is also holiday, that's 4-day
            thu = date_val - datetime.timedelta(days=1)
            if is_holiday(thu):
                results_fri_sat.append({
                    "start_date": thu.isoformat(),
                    "end_date": (date_val + datetime.timedelta(days=1)).isoformat(),
                    "length_days": 4,
                    "holiday_name": f"{holiday_dates[thu]['holiday_name']} + {h['holiday_name']}",
                    "states": holiday_states(date_val),
                })
            else:
                # Fri-Sat is the regular weekend, no extra day unless adjacent
                pass
        elif weekday == 5:  # Saturday
            # Saturday is weekend — check if Sunday is also a holiday for Fri-Sat states
            sun = date_val + datetime.timedelta(days=1)
            if is_holiday(sun):
                results_fri_sat.append({
                    "start_date": (date_val - datetime.timedelta(days=1)).isoformat(),
                    "end_date": sun.isoformat(),
                    "length_days": 3,
                    "holiday_name": f"{h['holiday_name']} + {holiday_dates[sun]['holiday_name']}",
                    "states": holiday_states(date_val),
                })

    # Deduplicate and sort
    def dedupe(results):
        seen = set()
        out = []
        for r in results:
            key = (r["start_date"], r["end_date"])
            if key not in seen:
                seen.add(key)
                out.append(r)
        return sorted(out, key=lambda x: x["start_date"])

    results_sat_sun = dedupe(results_sat_sun)
    results_fri_sat = dedupe(results_fri_sat)

    results = {
        "year": year,
        "sat_sun_states": sorted(SAT_SUN_STATES),
        "fri_sat_states": sorted(FRI_SAT_STATES),
        "sat_sun": results_sat_sun,
        "fri_sat": results_fri_sat,
    }

    out_file = f"malaysia_holidays_{year}_long_weekends.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== Long Weekends {year} (Sat-Sun states: {', '.join(sorted(SAT_SUN_STATES))}) ===")
    for lw in results_sat_sun:
        states_str = ", ".join(lw["states"]) if lw["states"] else "varies"
        print(f"  {lw['start_date']} to {lw['end_date']} ({lw['length_days']} days) — {lw['holiday_name']} [{states_str}]")

    print(f"\n=== Long Weekends {year} (Fri-Sat states: {', '.join(sorted(FRI_SAT_STATES))}) ===")
    for lw in results_fri_sat:
        states_str = ", ".join(lw["states"]) if lw["states"] else "varies"
        print(f"  {lw['start_date']} to {lw['end_date']} ({lw['length_days']} days) — {lw['holiday_name']} [{states_str}]")

    print(f"Long weekends saved to {out_file}")
    return out_file


if __name__ == "__main__":
    fetch()
    export_ics()
    long_weekends()