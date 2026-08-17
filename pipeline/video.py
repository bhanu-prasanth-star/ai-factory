"""Assembles the final vertical video with ffmpeg: a Ken Burns-style
pan/zoom over the scene images, narration + ducked background music,
and burned-in captions from the .srt file.

NOTE: ffmpeg filter graphs are sensitive to font availability and
ffmpeg build flags. Treat this as a solid starting point - render one
test video locally and check the subtitle styling/zoom speed before
trusting it in the unattended pipeline.
"""

import subprocess
import shlex

WIDTH, HEIGHT = 1080, 1920
FPS = 30


def get_audio_duration(audio_path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrapper=1:nokey=1", audio_path,
    ])
    return float(out.strip())


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

    filter_complex += (
        f";[vcat]subtitles={shlex.quote(srt_path)}:force_style="
        f"'FontName=DejaVu Sans Bold,FontSize=16,PrimaryColour=&HFFFFFF,"
        f"OutlineColour=&H000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=120'[vout]"
    )
    filter_complex += f";[{music_input_index}:a]volume=0.15[music]"
    filter_complex += f";[{audio_input_index}:a][music]amix=inputs=2:duration=first[aout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", audio_path,
        "-stream_loop", "-1", "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path
