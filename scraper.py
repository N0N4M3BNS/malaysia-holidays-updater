import requests, json, datetime
from bs4 import BeautifulSoup

URL_TEMPLATE = "https://www.officeholidays.com/countries/malaysia/{year}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch(year=None):
    year = year or datetime.datetime.now(datetime.UTC).year   # ← dynamic
    url = URL_TEMPLATE.format(year=year)
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")
    rows = soup.select("table tr")[1:]
    data = []
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        day, date_str, name, typ, comments = [td.get_text(strip=True) for td in tds[:5]]
        try:
            dt = datetime.datetime.strptime(f"{date_str} {year}", "%b %d %Y")
            iso_date = dt.strftime("%Y-%m-%d")
        except:
            iso_date = None
        data.append({"day": day, "date": date_str, "iso_date": iso_date,
                     "holiday_name": name, "type": typ, "comments": comments})
    out_file = f"malaysia_holidays_{year}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_file

if __name__ == "__main__":
    fetch()