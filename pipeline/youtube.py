import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload_short(video_path, title, description, hashtags, thumbnail_path=None):
    youtube = _get_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description + "\n\n" + " ".join(f"#{h}" for h in hashtags),
            "tags": hashtags[:15],
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            # Required disclosure as of YouTube's Oct 2024 API update for
            # realistic altered/synthetic content - keep this True since
            # every frame here is AI-generated.
            "containsSyntheticMedia": True,
        },
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response["id"]

    if thumbnail_path:
        youtube.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(thumbnail_path)
        ).execute()

    return f"https://www.youtube.com/shorts/{video_id}", video_id
