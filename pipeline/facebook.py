"""Publishes to a Facebook Page as a Reel via the Graph API's resumable
upload flow.

CAVEAT: this endpoint requires your Facebook app to pass Meta's app
review before it can post video on your behalf in production, and
Meta's upload APIs change more often than YouTube's. Test this one
manually against your Page before trusting it in the unattended
pipeline - it's the piece most likely to need adjustment.
"""

import os
import requests

GRAPH_VERSION = "v21.0"


def upload_reel(video_path, title, description, hashtags):
    page_id = os.environ["FB_PAGE_ID"]
    access_token = os.environ["FB_PAGE_TOKEN"]
    caption = f"{title}\n\n{description}\n\n" + " ".join(f"#{h}" for h in hashtags)

    init_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/video_reels"

    init_resp = requests.post(init_url, data={
        "upload_phase": "start",
        "access_token": access_token,
    })
    init_resp.raise_for_status()
    init_data = init_resp.json()
    video_id = init_data["video_id"]
    upload_url = init_data["upload_url"]

    with open(video_path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(os.path.getsize(video_path)),
            },
            data=f.read(),
        )
    upload_resp.raise_for_status()

    publish_resp = requests.post(init_url, data={
        "upload_phase": "finish",
        "video_id": video_id,
        "description": caption,
        "access_token": access_token,
    })
    publish_resp.raise_for_status()

    return f"https://www.facebook.com/reel/{video_id}", video_id
