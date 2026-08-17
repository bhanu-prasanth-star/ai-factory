"""GitHub's cron has no native 'every N days' interval, so this
workflow runs daily and this script decides whether today is actually
a publish day, by reading (never writing) a state row in Postgres.
The 'last_run_date' row is only written by run_pipeline.py, and only
after a real completion - so a crashed run never silently consumes a
publish slot."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.db import fetch_one

INTERVAL_DAYS = 2


def _set_output(name, value):
    gh_output_path = os.environ.get("GITHUB_OUTPUT")
    if gh_output_path:
        with open(gh_output_path, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"{name}={value}")


def main():
    row = fetch_one("SELECT value FROM pipeline_state WHERE key = 'last_run_date'")
    if row:
        last_run = date.fromisoformat(row["value"])
        if (date.today() - last_run).days < INTERVAL_DAYS:
            _set_output("run", "false")
            return
    _set_output("run", "true")


if __name__ == "__main__":
    main()