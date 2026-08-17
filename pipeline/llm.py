"""All LLM calls go through Google AI Studio's free Gemini tier via
plain REST, so there's no extra SDK dependency to manage."""

import os
import re
import json
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

TIMING_TEMPLATE = """
0-2 sec    : HOOK - a single startling line, no setup, no channel branding
2-8 sec    : SETUP - establish the premise in plain, concrete language
8-25 sec   : STORY - build the mystery, one idea per beat
25-40 sec  : ESCALATION - raise the stakes or reveal a complication
40-50 sec  : TWIST - the reveal that recontextualizes everything before it
Final sec  : LOOP - a line that connects back to the hook, inviting a rewatch
"""

THEMES = (
    "curiosity, wonder, science, technology, history, mysteries, "
    "fascinating human stories, futuristic concepts, nature, space, "
    "surprising facts, wholesome emotional stories, imaginative AI storytelling"
)

SAFETY_RULE = (
    "The content must be appropriate for ALL AGES: no violence, gore, "
    "sexual content, profanity, or anything designed to frighten young "
    "viewers. It should feel wondrous and safe, not disturbing."
)


def _call_gemini(prompt, expect_json=False):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if expect_json:
        payload["generationConfig"] = {"responseMimeType": "application/json"}
    resp = requests.post(GEMINI_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _clean_json(raw):
    raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(raw)


def generate_script(series_name, theme_description, episode_title, feedback=None):
    feedback_block = ""
    if feedback:
        feedback_block = (
            f"\nA previous attempt scored below the bar. Address this "
            f"feedback directly in the new version:\n{feedback}\n"
        )

    prompt = f"""
You are writing a ~50-second narrated YouTube Short script for the series
"{series_name}".
Series theme: {theme_description}

Episode title: "{episode_title}"

Follow this exact beat structure:
{TIMING_TEMPLATE}

Lean into these themes wherever they fit naturally: {THEMES}

{SAFETY_RULE}
{feedback_block}
Write ONLY the narration text the voiceover will read, broken into short
lines, one line per beat, each line prefixed with its beat name in
brackets, e.g.:
[HOOK] ...
[SETUP] ...
[STORY] ...
[ESCALATION] ...
[TWIST] ...
[LOOP] ...

Keep total spoken word count between 110 and 150 words so it fits ~50
seconds at a natural narration pace. No preamble, no title, no
explanation outside the bracketed lines - narration only.
"""
    return _call_gemini(prompt).strip()


def score_script(series_name, episode_title, script_text):
    prompt = f"""
You are a strict YouTube Shorts script editor scoring a script for the
series "{series_name}", episode "{episode_title}".

Score the script below against these 6 categories. Return ONLY valid
JSON, no markdown fences, no commentary outside the JSON object.

Categories and max points:
- hook_score (0-25): Does the first line grab attention instantly with
  zero preamble?
- structure_score (0-15): Does it follow the 6-beat timing structure
  proportionally?
- payoff_score (0-20): Does the twist genuinely recontextualize the
  story, not a letdown?
- loop_score (0-15): Does the ending connect back to the hook, inviting
  a rewatch?
- safety_score (0-15): Is it fully appropriate for all ages - no
  violence, gore, or scares intense enough to disturb a young viewer?
- tone_score (0-10): Does it fit a curious, wonder-driven, wholesome
  tone?

JSON shape:
{{
  "hook_score": <int>, "structure_score": <int>, "payoff_score": <int>,
  "loop_score": <int>, "safety_score": <int>, "tone_score": <int>,
  "total_score": <int, sum of the above>,
  "critique": "<2-3 sentences of specific, actionable feedback>"
}}

Script:
{script_text}
"""
    return _clean_json(_call_gemini(prompt, expect_json=True))


def generate_metadata(series_name, episode_title, script_text):
    prompt = f"""
Based on this YouTube Short script from the series "{series_name}",
episode "{episode_title}", generate metadata. Return ONLY valid JSON:

{{
  "title": "<under 100 chars, curiosity-driven, no clickbait lies>",
  "description": "<2-3 sentences plus a soft CTA to follow for more>",
  "hashtags": ["<8-12 relevant hashtags, no # symbol>"]
}}

Script:
{script_text}
"""
    return _clean_json(_call_gemini(prompt, expect_json=True))
