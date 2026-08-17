"""Optional human checkpoint: sends the finished video + score to a
Telegram chat so you can glance at it before/after it publishes.
Fully free via the Telegram Bot API. If not configured, calls are
silently skipped so the pipeline still runs end to end."""

import os
import requests


def notify(message, video_path=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured, skipping notification:", message)
        return

    base = f"https://api.telegram.org/bot{token}"
    requests.post(f"{base}/sendMessage", data={"chat_id": chat_id, "text": message})

    if video_path:
        with open(video_path, "rb") as f:
            requests.post(f"{base}/sendVideo", data={"chat_id": chat_id}, files={"video": f})
