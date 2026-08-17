# YouTube Shorts / Facebook Reels automation

Fully free pipeline: idea → script → score gate (≥80/100) → voiceover
→ visuals → assembly → publish → analytics logging. Runs on GitHub
Actions, storage in a free Neon Postgres database.

## 0. Prerequisite: database

You should already have a Neon project with the 6 core tables created.
Run `schema_additions.sql` once in the Neon SQL Editor too - it adds
one more small table (`pipeline_state`) that the every-2-days
scheduling gate needs.

## 1. Required GitHub secrets

Go to your repo's **Settings → Secrets and variables → Actions** and
add each of these (see `.env.example` for the full list of names):

| Secret | Where to get it |
|---|---|
| `DATABASE_URL` | Neon dashboard → Connect (use the **pooled** connection string) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) → Get API key (free tier) |
| `POLLINATIONS_API_KEY` | [enter.pollinations.ai](https://enter.pollinations.ai) → free signup |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | See step 2 below |
| `YT_API_KEY` | Google Cloud Console → Credentials → API key (for the analytics pull; needs YouTube Data API v3 enabled) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | See step 4 below - **required** for now, since it's how you receive the video for manual Facebook posting (see step 3) |

## 2. One-time YouTube OAuth setup

1. In [Google Cloud Console](https://console.cloud.google.com), create
   a project and enable **YouTube Data API v3**.
2. Create an OAuth 2.0 Client ID of type **Desktop app**, download it
   as `client_secret.json` into this repo folder (don't commit it).
3. Locally: `pip install google-auth-oauthlib` then
   `python scripts/get_youtube_refresh_token.py`. A browser window
   opens for you to approve access once.
4. It prints your `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, and
   `YT_REFRESH_TOKEN` - add all three as GitHub secrets. This refresh
   token keeps working indefinitely, so this is a one-time step.

## 3. Facebook - currently manual, not automated

Automated Facebook posting is **disabled** in this version of the
pipeline. `pipeline/facebook.py` still exists if you want to revisit
it later, but `scripts/run_pipeline.py` no longer calls it.

Instead, once a YouTube upload succeeds, the pipeline sends you a
Telegram message with the finished video attached and a ready-to-paste
caption (title + description + hashtags) - you post it to Facebook by
hand. This needs the Telegram bot from step 4 configured.

If you want to re-enable full Facebook automation later: a Page access
token via a properly reviewed Meta app (not a personal profile) is the
supported path, and it's worth knowing that creating a second personal
profile specifically to route around a restriction is against Meta's
terms - accounts made to evade an enforcement action can themselves
get flagged, especially if they're later linked to the same Business
Manager, app, phone number, or device. If you go the second-profile
route anyway, keep it fully separate from any Business Manager or app
tied to your original account.

## 4. Telegram review bot (optional, free, recommended)

1. Message **@BotFather** on Telegram, send `/newbot`, follow the
   prompts - you get a bot token.
2. Message your new bot once (anything), then visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser to
   find your `chat.id`.
3. Add both as `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. If you
   skip this, the pipeline still runs - it just won't send you a
   preview before publishing.

## 5. Add background music

Drop one royalty-free instrumental track at
`assets/background_music.mp3` - see `assets/README.md` for free
sources.

## 6. Test it

Trigger the workflow manually first rather than waiting for the
schedule: **Actions tab → Generate and Publish Short → Run workflow**.
Watch the logs. The parts most worth checking on a first run:

- **`pipeline/video.py`** - ffmpeg filter graphs are sensitive to font
  availability and build flags. If subtitle burning fails, check the
  font name in `force_style` matches a font actually installed on the
  runner (`fc-list | grep -i dejavu`).
- **`pipeline/facebook.py`** - the piece most likely to need
  adjustment, since it depends on your app review status and Meta's
  API version.
- **`pipeline/tts.py`** - edge-tts is an actively maintained but
  unofficial wrapper; if the `SubMaker` API errors, check the
  installed version's docs.

## How the schedule works

GitHub cron has no native "every 2 days" option, so the workflow runs
**daily**, and `scripts/should_run_today.py` checks a `pipeline_state`
row in Postgres to decide whether to actually proceed. This also means
if a run fails partway, the next day's run won't skip itself - it'll
retry.

## Repo structure

```
.github/workflows/
  publish-short.yml     - main pipeline, scheduled every ~2 days
  pull-analytics.yml    - daily performance snapshot pull
pipeline/
  db.py                 - Postgres helpers
  llm.py                - script generation, scoring, metadata (Gemini)
  tts.py                - voiceover + captions (edge-tts)
  visuals.py             - scene images (Pollinations) + thumbnail (Pillow)
  video.py               - ffmpeg assembly
  youtube.py              - YouTube Data API upload
  facebook.py             - Facebook Graph API upload (currently unused - see step 3)
  telegram_notify.py      - sends previews + the manual-FB-post handoff
scripts/
  run_pipeline.py               - orchestrates the whole flow end to end
  should_run_today.py           - every-2-days scheduling gate
  pull_analytics.py             - performance snapshot job
  get_youtube_refresh_token.py  - one-time local OAuth helper
schema_additions.sql     - one more table beyond the original 6
assets/                  - put background_music.mp3 here
```
