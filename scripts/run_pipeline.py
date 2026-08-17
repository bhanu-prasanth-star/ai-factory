import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.db import fetch_one, execute
from pipeline import llm, tts, visuals, video as video_module, youtube, telegram_notify

SCORE_THRESHOLD = 80
MAX_ATTEMPTS = 3


def get_next_episode():
    ep = fetch_one(
        "SELECT e.episode_id, e.title, e.episode_number, s.name AS series_name, "
        "s.theme_description FROM episodes e JOIN series s ON e.series_id = s.series_id "
        "WHERE e.status = 'queued' ORDER BY e.episode_number ASC LIMIT 1"
    )
    if ep:
        execute("UPDATE episodes SET status = 'in_progress' WHERE episode_id = %s", (ep["episode_id"],))
    return ep


def scene_prompts_from_script(script_text, series_name):
    """Turn each bracketed beat line into an image-generation prompt."""
    prompts = []
    for line in script_text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        text = line.split("]", 1)[1].strip()
        prompts.append(
            f"cinematic atmospheric illustration for a mystery short titled "
            f"'{series_name}': {text}, moody lighting, no text, no watermark, "
            f"vertical composition"
        )
    return prompts


def run():
    episode = get_next_episode()
    if not episode:
        print("No queued episodes. Add more rows to the `episodes` table.")
        return

    script_text, score, feedback = None, None, None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        script_text = llm.generate_script(
            episode["series_name"], episode["theme_description"], episode["title"], feedback
        )
        result = llm.score_script(episode["series_name"], episode["title"], script_text)
        score = result["total_score"]

        execute(
            "INSERT INTO scripts (episode_id, attempt_number, script_text, hook_score, "
            "structure_score, payoff_score, loop_score, safety_score, tone_score, "
            "total_score, passed) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (episode["episode_id"], attempt, script_text, result["hook_score"],
             result["structure_score"], result["payoff_score"], result["loop_score"],
             result["safety_score"], result["tone_score"], score, score >= SCORE_THRESHOLD),
        )

        print(f"Attempt {attempt}: score {score}/100")
        if score >= SCORE_THRESHOLD:
            break
        feedback = result["critique"]
    else:
        execute("UPDATE episodes SET status = 'rejected' WHERE episode_id = %s", (episode["episode_id"],))
        telegram_notify.notify(
            f"Episode '{episode['title']}' failed scoring after {MAX_ATTEMPTS} attempts "
            f"(last score {score}). Needs manual review."
        )
        return

    metadata = llm.generate_metadata(episode["series_name"], episode["title"], script_text)

    audio_path, srt_path = tts.generate_voiceover(script_text)
    scene_prompts = scene_prompts_from_script(script_text, episode["series_name"])
    scene_paths = visuals.generate_scene_images(scene_prompts)
    thumbnail_path = visuals.make_thumbnail(scene_paths[0], metadata["title"])
    final_video = video_module.assemble_video(
        scene_paths, audio_path, srt_path, music_path="assets/background_music.mp3"
    )

    telegram_notify.notify(
        f"Publishing: {metadata['title']} (score {score}/100)", video_path=final_video
    )

    yt_url, yt_id = youtube.upload_short(
        final_video, metadata["title"], metadata["description"], metadata["hashtags"], thumbnail_path
    )

    script_row = fetch_one(
        "SELECT script_id FROM scripts WHERE episode_id=%s ORDER BY script_id DESC LIMIT 1",
        (episode["episode_id"],),
    )
    video_row = execute(
        "INSERT INTO videos (script_id, thumbnail_path) VALUES (%s, %s) RETURNING video_id",
        (script_row["script_id"], thumbnail_path),
        returning=True,
    )
    execute(
        "INSERT INTO publications (video_id, platform, platform_video_id, title, "
        "description, hashtags, published_at) VALUES (%s,'youtube',%s,%s,%s,%s, now())",
        (video_row["video_id"], yt_id, metadata["title"], metadata["description"],
         ",".join(metadata["hashtags"])),
    )

    # Facebook auto-posting is disabled for now (see README) - hand off
    # for manual posting instead: ready-to-paste caption + the video
    # file, both delivered via the same Telegram bot.
    fb_caption = (
        f"{metadata['title']}\n\n{metadata['description']}\n\n"
        + " ".join(f"#{h}" for h in metadata["hashtags"])
    )
    telegram_notify.notify(
        f"YouTube is live: {yt_url}\n\n"
        f"Post this to Facebook manually - caption below, video attached:\n\n{fb_caption}",
        video_path=final_video,
    )

    execute("UPDATE episodes SET status = 'produced' WHERE episode_id = %s", (episode["episode_id"],))
    print("Done:", yt_url)


if __name__ == "__main__":
    run()
