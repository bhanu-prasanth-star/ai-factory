"""Run this ONCE on your own machine (never in GitHub Actions) to get a
YouTube refresh token that the automated pipeline can then use forever
without you re-authenticating.

Prerequisites:
1. In Google Cloud Console, create a project and enable the
   'YouTube Data API v3'.
2. Create an OAuth 2.0 Client ID of type 'Desktop app'.
3. Download it as client_secret.json into this same folder.

Usage:
    pip install google-auth-oauthlib
    python scripts/get_youtube_refresh_token.py
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)

print("\nAdd these as GitHub repo secrets (Settings > Secrets and variables > Actions):\n")
print("YT_CLIENT_ID     =", creds.client_id)
print("YT_CLIENT_SECRET =", creds.client_secret)
print("YT_REFRESH_TOKEN =", creds.refresh_token)
