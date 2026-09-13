# YTM-BB100

Scrapes Billboard chart data (Hot 100 / Global 200, year-end and weekly), matches each
entry to a YouTube Music song and official video, and syncs the results into YouTube
Music playlists.

## Files

- **`create-chart.py`** — scrapes Billboard and writes chart data to `charts/`.
- **`update-playlist.py`** — reads a chart JSON file and creates/syncs the corresponding
  YouTube Music playlists.
- **`charts/`** — output data, organized as:
  - `charts/year-end/<hot-100|global-200>/<year>.json`
  - `charts/week/<year>/<hot-100|global-200>/<YYYY-Www>.json` (one snapshot per ISO week)
  - `charts/week/<year>/<hot-100|global-200>/latest.json` (always the most recent week;
    its playlist IDs stay fixed across updates)

## Chart JSON format

```json
{
  "week": "2026-W37",
  "date": "2026-09-12",
  "chart": "Hot 100 Songs",
  "description": "Billboard Hot 100 Songs | Auto-updated weekly. | Chart week: 2026-09-12",
  "playlist_songYt": "PLxxxxxxxxxxxxxxxx",
  "playlist_videoYt": "PLxxxxxxxxxxxxxxxx",
  "entries": [
    {
      "rank": 1,
      "song": "Choosin' Texas",
      "artist": "Ella Langley",
      "songYt": "xukbqwRuN5w",
      "videoYt": "hLOheGDwD_0"
    }
  ]
}
```

Year-end files use `"year"` instead of `"week"`/`"date"`, and their `"description"` reads
`"Billboard {chart} | Year-End {year}"` instead.

## Contributing

Spotted a wrong song or video match? Don't just live with it — fix it! Automatic
matching isn't perfect, and every correction makes these playlists better for everyone
listening to them.

Found the right YouTube Music video ID? Open a PR editing the `"songYt"` or `"videoYt"`
value directly in the chart JSON file. That's it — no scripts to run, no setup required.
I'll get it pushed to the live playlist soon after. Contributions welcome!
