"""GitHub's cron has no native 'every N days' interval, so this
workflow runs daily and this script decides whether today is actually
a publish day, using a state row stored in Postgres."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.db import fetch_one, execute

INTERVAL_DAYS = 2


def _set_output(name, value):
    gh_output_path = os.environ.get("GITHUB_OUTPUT")
    if gh_output_path:
        with open(gh_output_path, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"{name}={value}")


def main():
    row = fetch_one("SELECT value FROM pipeline_state WHERE key = 'last_run_date'")
    today = date.today()

    if row:
        last_run = date.fromisoformat(row["value"])
        if (today - last_run).days < INTERVAL_DAYS:
            _set_output("run", "false")
            return

    execute(
        "INSERT INTO pipeline_state (key, value) VALUES ('last_run_date', %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (today.isoformat(),),
    )
    _set_output("run", "true")


if __name__ == "__main__":
    main()
