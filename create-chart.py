import json
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from ytmusicapi import YTMusic

CHARTS = {
    "hot-100": {
        "chart_name": "Hot 100 Songs",
        "year_end_url": "https://www.billboard.com/charts/year-end/{year}/hot-100-songs/",
        "week_url": "https://www.billboard.com/charts/hot-100/",
    },
    "global-200": {
        "chart_name": "Global 200 Songs",
        "year_end_url": "https://www.billboard.com/charts/year-end/{year}/billboard-global-200/",
        "week_url": "https://www.billboard.com/charts/billboard-global-200/",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def scrape_entries(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("div.o-chart-results-list-row-container")

    entries = []
    for i, row in enumerate(rows, start=1):
        title_tag = row.select_one("h3.c-title")
        artist_tag = title_tag.find_next_sibling("span") if title_tag else None

        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        artist = " ".join(artist_tag.get_text(" ", strip=True).split()) if artist_tag else "N/A"

        entries.append({"rank": i, "song": title, "artist": artist})
    return entries


def first_result(results):
    if not results:
        return None
    return results[0].get("videoId")


def first_official_video(results):
    for r in results:
        if r.get("videoType") == "MUSIC_VIDEO_TYPE_OMV":
            return r.get("videoId")
    return first_result(results)


def fill_youtube_ids(entries):
    ytmusic = YTMusic()
    for entry in entries:
        query = f"{entry['song']} {entry['artist']}"
        songs = ytmusic.search(query, filter="songs", limit=10, ignore_spelling=True)
        videos = ytmusic.search(f"{query} Official Music Video", filter="videos", limit=10, ignore_spelling=True)
        entry["songYt"] = first_result(songs)
        entry["videoYt"] = first_official_video(videos)


def run_year_end(chart_key):
    chart = CHARTS[chart_key]
    year = datetime.now().year - 1
    output_path = os.path.join("charts", "year-end", chart_key, f"{year}.json")

    if os.path.exists(output_path):
        print(f"{output_path} already exists and {year} is the latest year-end chart available. Skipping.")
        return

    url = chart["year_end_url"].format(year=year)
    response = requests.get(url, headers=HEADERS, timeout=30)
    entries = scrape_entries(response.text)
    fill_youtube_ids(entries)

    data = {
        "year": year,
        "chart": chart["chart_name"],
        "description": f"Billboard {chart['chart_name']} | Year-End {year}",
        "playlist_songYt": "",
        "playlist_videoYt": "",
        "entries": entries,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(entries)} entries to {output_path}")


def run_week(chart_key):
    chart = CHARTS[chart_key]
    current_year, current_week, _ = datetime.now().isocalendar()
    expected_week_id = f"{current_year}-W{current_week:02d}"
    expected_path = os.path.join("charts", "week", str(current_year), chart_key, f"{expected_week_id}.json")

    if os.path.exists(expected_path):
        print(f"[pre-check] {expected_path} already exists for the current ISO week ({expected_week_id}). Skipping.")
        return

    response = requests.get(chart["week_url"], headers=HEADERS, timeout=30)
    response.raise_for_status()

    title_tag = BeautifulSoup(response.text, "html.parser").select_one("div.charts-title")
    date_match = re.search(r"Week of ([A-Za-z]+ \d{1,2}, \d{4})", title_tag.get_text()) if title_tag else None
    if not date_match:
        raise RuntimeError(f"Could not find chart date on {chart['week_url']} - page structure may have changed")

    chart_date = datetime.strptime(date_match.group(1), "%B %d, %Y")
    chart_date_str = chart_date.strftime("%Y-%m-%d")
    iso_year, iso_week, _ = chart_date.isocalendar()
    week_id = f"{iso_year}-W{iso_week:02d}"

    actual_path = os.path.join("charts", "week", str(iso_year), chart_key, f"{week_id}.json")
    if os.path.exists(actual_path):
        print(f"[billboard-check] {actual_path} already exists - Billboard still shows {week_id} as the latest chart. Skipping.")
        return

    entries = scrape_entries(response.text)
    if not entries:
        raise RuntimeError(f"No entries scraped from {chart['week_url']} - page structure may have changed")

    fill_youtube_ids(entries)

    chart_line = f"Billboard {chart['chart_name']}"
    data = {
        "week": week_id,
        "date": chart_date_str,
        "chart": chart["chart_name"],
        "description": f"{chart_line} | Chart week: {chart_date_str}",
        "playlist_songYt": "",
        "playlist_videoYt": "",
        "entries": entries,
    }

    output_dir = os.path.join("charts", "week", str(iso_year), chart_key)
    os.makedirs(output_dir, exist_ok=True)

    week_path = os.path.join(output_dir, f"{week_id}.json")
    with open(week_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    latest_path = os.path.join(output_dir, "latest.json")
    latest_data = dict(data)
    latest_data["description"] = f"{chart_line} | Auto-updated weekly. | Chart week: {chart_date_str}"
    if os.path.exists(latest_path):
        with open(latest_path, "r", encoding="utf-8") as f:
            previous_latest = json.load(f)
        latest_data["playlist_songYt"] = previous_latest.get("playlist_songYt", "")
        latest_data["playlist_videoYt"] = previous_latest.get("playlist_videoYt", "")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(latest_data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(entries)} entries to {week_path} and {latest_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("year-end", "week") or sys.argv[2] not in CHARTS:
        sys.exit(f"Usage: python create.py <year-end|week> <{'|'.join(CHARTS)}>")

    period, chart_key = sys.argv[1], sys.argv[2]
    if period == "year-end":
        run_year_end(chart_key)
    else:
        run_week(chart_key)
