# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated Python scraper that fetches Malaysia public holidays from OfficeHolidays.com, outputs them as JSON, and keeps them updated monthly via GitHub Actions. Single-source-file project — `scraper.py` is the entire application.

## Commands

- **Install dependencies**: `pip install -r requirements.txt`
- **Run scraper (current year)**: `python scraper.py`
- **Run scraper for a specific year**: `python -c "from scraper import fetch; fetch(2024)"`
- No test suite, linter, or formatter is configured.

## Architecture

- `scraper.py` — The sole script. `fetch(year)` scrapes `https://www.officeholidays.com/countries/malaysia/{year}`, parses HTML tables with BeautifulSoup, filters non-holidays, deduplicates, parses states, and writes `malaysia_holidays_{year}.json`. Returns the output filename.
- `malaysia_holidays_{year}.json` — Output artifact: a JSON object with `year`, `source`, and `holidays` array. Each holiday has `date` (ISO), `holiday_name`, `type` ("National"/"Regional"/"Government"), optional `states` array (for non-National), and optional `description`.
- `.github/workflows/update-holidays.yml` — GitHub Actions workflow: runs monthly (1st at 00:15 UTC) and on manual dispatch. Uses `python-version: "3.x"`, auto-commits changed JSON with message `chore: auto-update Malaysia holidays for {YEAR}`.

## Key Details

- **Python 3.11+ required** — uses `datetime.UTC` (added in 3.11).
- **Data source**: OfficeHolidays.com web scraping — site structure changes will break the parser.
- **Data processing pipeline**: scrape → parse HTML tables → filter "Not A Public Holiday" → deduplicate by (date, name) → parse states from comments → extract descriptions → sort by date → write JSON.
- **State parsing**: Comments like "Except Kelantan" or "Kedah, Perlis and Negeri Sembilan" are parsed into structured `states` arrays against a canonical list of 16 Malaysian states/territories. "Most states", "Several states" etc. result in `states: null`.
- **National holidays omit `states`** — implied to be all states. Regional/Government holidays always have a `states` field (may be `null` if indeterminate).
- **Commit convention for automated updates**: `chore: auto-update Malaysia holidays for {YEAR}`.