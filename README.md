# 🇲🇾 Malaysia Holidays Updater

An automated Python scraper that fetches and updates Malaysia's public holidays data from [OfficeHolidays.com](https://www.officeholidays.com/countries/malaysia) on a monthly basis using GitHub Actions.

[![Update Malaysia Holidays](https://github.com/N0N4M3BNS/malaysia-holidays-updater/actions/workflows/update-holidays.yml/badge.svg)](https://github.com/N0N4M3BNS/malaysia-holidays-updater/actions/workflows/update-holidays.yml)

## 📊 Data Format

The scraper generates JSON files with structured holiday data designed for developer consumption:

```json
{
  "year": 2025,
  "source": "officeholidays.com",
  "holidays": [
    {
      "date": "2025-01-29",
      "holiday_name": "Chinese New Year",
      "type": "National",
      "description": "1st day of 1st lunar month"
    },
    {
      "date": "2025-01-30",
      "holiday_name": "Chinese New Year Holiday",
      "type": "Regional",
      "states": ["Johor", "Kedah", "Melaka", "..."]
    },
    {
      "date": "2025-04-18",
      "holiday_name": "Good Friday",
      "type": "Regional",
      "states": ["Sabah", "Sarawak"]
    }
  ]
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO 8601 date (`YYYY-MM-DD`), `null` if unparseable |
| `holiday_name` | string | Name of the holiday |
| `type` | string | `"National"`, `"Regional"`, or `"Government"` |
| `states` | array\|null | List of observing states/territories (Regional/Government only; omitted for National) |
| `description` | string | Additional context (only present when meaningful) |

> **Note**: Non-public holidays (e.g., Mother's Day, Father's Day) are filtered out. Duplicate entries from the source are merged.

## 🚀 Features

- **Automated Updates**: Runs monthly via GitHub Actions
- **Comprehensive Coverage**: Includes national, regional, and state-specific holidays
- **Clean Data**: Structured JSON with ISO dates, parsed state lists, deduplicated entries
- **Manual Trigger**: Can be run on-demand from GitHub Actions
- **Zero Maintenance**: Fully automated with intelligent change detection

## 🛠️ Installation & Local Development

### Prerequisites

- Python 3.7+
- pip package manager

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/N0N4M3BNS/malaysia-holidays-updater.git
   cd malaysia-holidays-updater
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally**
   ```bash
   python scraper.py
   ```

This will generate `malaysia_holidays_2025.json` (or current year) in the project root.

## 🔄 Automation

### GitHub Actions Workflow

The project uses GitHub Actions for automated monthly updates:

- **Schedule**: Runs at 00:15 UTC on the 1st of every month
- **Trigger**: Also supports manual execution
- **Change Detection**: Only commits when data actually changes
- **Bot Commits**: Uses GitHub Actions bot for automated commits

### Workflow Details

| Setting          | Value                        |
| ---------------- | ---------------------------- |
| **Schedule**     | `15 0 1 * *` (Monthly)       |
| **Runner**       | `ubuntu-latest`              |
| **Python**       | Latest 3.x                   |
| **Dependencies** | `requests`, `beautifulsoup4` |

## 📁 Project Structure

```
malaysia-holidays-updater/
├── .github/
│   └── workflows/
│       └── update-holidays.yml    # GitHub Actions workflow
├── malaysia_holidays_2025.json   # Generated data (example)
├── requirements.txt               # Python dependencies
├── scraper.py                     # Main scraper script
├── README.md                      # This file
└── .gitignore                     # Git ignore rules
```

## 🔧 Technical Details

### Data Source

- **Website**: OfficeHolidays.com Malaysia page
- **URL Pattern**: `https://www.officeholidays.com/countries/malaysia/{year}`
- **Scraping Method**: BeautifulSoup4 with requests
- **User Agent**: Standard browser user agent

### Data Processing

1. **HTML Parsing**: Extracts table rows from holiday listings
2. **Date Standardization**: Converts month-day strings to ISO format
3. **Filtering**: Removes "Not A Public Holiday" entries (e.g., Mother's Day)
4. **Deduplication**: Merges entries with the same date and name, combining state info
5. **State Parsing**: Extracts structured state lists from free-text comments (handles "Except X", "X and Y", abbreviations like KDH/KTN/TRG)
6. **Description Extraction**: Preserves meaningful context (e.g., "End of Ramadan") while omitting state-only comments
7. **JSON Export**: Saves as pretty-printed UTF-8 JSON

### Error Handling

- **Graceful Failure**: Continues processing even with malformed dates
- **ISO Date Fallback**: Sets `date: null` for unparseable dates
- **Row Validation**: Skips rows with insufficient data

## 📈 Usage Examples

### Local Testing

```bash
# Generate data for specific year
python -c "from scraper import fetch; fetch(2024)"

# Check current year data
python scraper.py && cat malaysia_holidays_2025.json | jq '.holidays[] | select(.type=="National")'
```

### API Integration

```python
import json
import requests

# Fetch latest data from GitHub
url = "https://raw.githubusercontent.com/N0N4M3BNS/malaysia-holidays-updater/main/malaysia_holidays_2025.json"
response = requests.get(url)
holidays = response.json()

# Filter national holidays
national_holidays = [h for h in holidays['holidays'] if h['type'] == 'National']
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Test locally**: Run `python scraper.py` and verify output
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request**

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

- **Issues**: Report bugs via [GitHub Issues](https://github.com/N0N4M3BNS/malaysia-holidays-updater/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/N0N4M3BNS/malaysia-holidays-updater/discussions)
- **Data Issues**: Contact OfficeHolidays.com for holiday accuracy concerns

---

**Made with ❤️ for the Malaysia developer community**
