"""Assembles the final vertical video with ffmpeg: a Ken Burns-style
pan/zoom over the scene images, narration + ducked background music,
and burned-in captions from the .srt file (when one is available).

NOTE: ffmpeg filter graphs are sensitive to font availability and
ffmpeg build flags. Treat this as a solid starting point - render one
test video locally and check the subtitle styling/zoom speed before
trusting it in the unattended pipeline.
"""

import os
import shlex
import subprocess

WIDTH, HEIGHT = 1080, 1920
FPS = 30


def get_audio_duration(audio_path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
    ])
    return float(out.strip())


def _has_valid_captions(srt_path):
    """A genuinely empty/broken .srt (e.g. no WordBoundary events came
    back from the TTS stream on a given run) makes ffmpeg's subtitles
    filter fail to even open it - not a warning, a hard crash. Better
    to publish without burned captions once than lose the whole video
    over it."""
    if not srt_path or not os.path.exists(srt_path):
        return False
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return "-->" in content  # the SRT timestamp arrow - proof of at least one real cue


def assemble_video(scene_paths, audio_path, srt_path, music_path, out_path="short.mp4"):
    duration = get_audio_duration(audio_path)
    per_scene = duration / len(scene_paths)

    inputs = []
    filter_parts = []
    for i, scene in enumerate(scene_paths):
        inputs += ["-loop", "1", "-t", f"{per_scene:.2f}", "-i", scene]
        filter_parts.append(
            f"[{i}:v]scale={WIDTH*2}:{HEIGHT*2},"
            f"zoompan=z='min(zoom+0.0015,1.2)':d={int(per_scene*FPS)}:"
            f"s={WIDTH}x{HEIGHT}:fps={FPS}[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(scene_paths)))
    filter_complex = (
        ";".join(filter_parts)
        + f";{concat_inputs}concat=n={len(scene_paths)}:v=1:a=0[vcat]"
    )

    audio_input_index = len(scene_paths)
    music_input_index = audio_input_index + 1

    if _has_valid_captions(srt_path):
        filter_complex += (
            f";[vcat]subtitles={shlex.quote(srt_path)}:force_style="
            f"'FontName=DejaVu Sans Bold,FontSize=16,PrimaryColour=&HFFFFFF,"
            f"OutlineColour=&H000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=120'[vout]"
        )
    else:
        print(f"WARNING: no usable captions at '{srt_path}' - publishing without burned-in captions this run.")
        filter_complex += ";[vcat]copy[vout]"

    filter_complex += f";[{music_input_index}:a]volume=0.15[music]"
    filter_complex += f";[{audio_input_index}:a][music]amix=inputs=2:duration=first[aout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", audio_path,
        "-stream_loop", "-1", "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-c:a", "aac",
        # -shortest alone is unreliable here: the background music input
        # loops infinitely (-stream_loop -1), and -shortest doesn't
        # always cut a complex filtergraph cleanly against an infinite
        # input. Cap the output explicitly at the real narration length
        # instead of trusting -shortest to figure it out.
        "-t", f"{duration:.2f}",
        "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path
