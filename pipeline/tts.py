"""Free narration via edge-tts (wraps Microsoft Edge's cloud TTS,
no API key). Also emits an .srt file for burned-in captions."""

import asyncio
import re
import edge_tts

VOICE = "en-US-AriaNeural"


def strip_beat_labels(script_text):
    """Turn '[HOOK] Something happened.' into 'Something happened.'"""
    lines = []
    for line in script_text.splitlines():
        line = re.sub(r"^\[[A-Z]+\]\s*", "", line.strip())
        if line:
            lines.append(line)
    return " ".join(lines)


async def _synthesize(text, audio_path, srt_path):
    communicate = edge_tts.Communicate(text, VOICE)
    submaker = edge_tts.SubMaker()
    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(submaker.get_srt())


def generate_voiceover(script_text, audio_path="voice.mp3", srt_path="captions.srt"):
    narration = strip_beat_labels(script_text)
    asyncio.run(_synthesize(narration, audio_path, srt_path))
    return audio_path, srt_path
