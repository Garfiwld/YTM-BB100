import json
import os
import sys

from ytmusicapi import YTMusic

# YouTube Music API rejects or silently truncates requests with too many items at once
CHUNK_SIZE = 100


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def add_items(ytmusic, playlist_id, video_ids):
    for chunk in chunks(video_ids, CHUNK_SIZE):
        ytmusic.add_playlist_items(playlist_id, chunk, duplicates=True)


def remove_tracks(ytmusic, playlist_id, tracks):
    for chunk in chunks(tracks, CHUNK_SIZE):
        ytmusic.remove_playlist_items(playlist_id, chunk)


def sync_playlist(ytmusic, playlist_id, title, description, video_ids):
    if not playlist_id:
        playlist_id = ytmusic.create_playlist(title, description, privacy_status="PUBLIC")
        if video_ids:
            add_items(ytmusic, playlist_id, video_ids)
        return playlist_id

    ytmusic.edit_playlist(playlist_id, title=title, description=description)

    current = ytmusic.get_playlist(playlist_id, limit=None)
    if current["tracks"]:
        remove_tracks(ytmusic, playlist_id, current["tracks"])

    if video_ids:
        add_items(ytmusic, playlist_id, video_ids)

    return playlist_id


def build_title(data, is_latest):
    if "year" in data:
        return f"Year End {data['year']} | {data['chart']}"
    if is_latest:
        return f"Latest | {data['chart']}"
    return f"Week {data['week']} | {data['chart']}"


def main(chart_path):
    is_latest = os.path.basename(chart_path) == "latest.json"

    with open(chart_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data["entries"]
    songs_ids = [e["songYt"] for e in entries if e.get("songYt")]
    mv_ids = [e["videoYt"] or e["songYt"] for e in entries if e.get("videoYt") or e.get("songYt")]

    title = build_title(data, is_latest)
    mv_title = f"{title} MV"
    description = data["description"]

    ytmusic = YTMusic("browser.json")

    songs_playlist_id = sync_playlist(ytmusic, data.get("playlist_songYt") or None, title, description, songs_ids)
    mv_playlist_id = sync_playlist(ytmusic, data.get("playlist_videoYt") or None, mv_title, description, mv_ids)

    data["playlist_songYt"] = songs_playlist_id
    data["playlist_videoYt"] = mv_playlist_id

    with open(chart_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{title}: https://music.youtube.com/playlist?list={songs_playlist_id}")
    print(f"{mv_title}: https://music.youtube.com/playlist?list={mv_playlist_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python update-playlist.py <path-to-chart.json>")
    main(sys.argv[1])
