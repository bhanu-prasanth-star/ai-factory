import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from pipeline.db import fetch_all, execute


def pull_youtube_stats(platform_video_id):
    api_key = os.environ["YT_API_KEY"]  # a plain API key is enough for public stats
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "statistics", "id": platform_video_id, "key": api_key},
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        return None
    stats = items[0]["statistics"]
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
    }


def run():
    pubs = fetch_all(
        "SELECT publication_id, platform_video_id FROM publications WHERE platform='youtube'"
    )
    for pub in pubs:
        stats = pull_youtube_stats(pub["platform_video_id"])
        if not stats:
            continue
        execute(
            "INSERT INTO analytics_snapshots (publication_id, views, likes, comments) "
            "VALUES (%s, %s, %s, %s)",
            (pub["publication_id"], stats["views"], stats["likes"], stats["comments"]),
        )
    print(f"Logged snapshots for {len(pubs)} YouTube publications.")
    # A Facebook Insights pull can be added here once your app review is approved.


if __name__ == "__main__":
    run()
