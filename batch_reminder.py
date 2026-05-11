from __future__ import annotations

import argparse
import os
import sys

from biometrics_core import (
    TODAY_REMINDER_PATH,
    current_date_iso,
    generate_reminder_message,
    get_latest_previous_row,
    load_data,
    load_metadata,
)
import slack_notify


DEFAULT_APP_URL = "https://ligibiometrics.streamlit.app/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate today's Ligi Biometrics check-in reminder.")
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the reminder only and do not write data/today_reminder.txt.",
    )
    parser.add_argument(
        "--slack",
        action="store_true",
        help="Post the reminder to the configured Slack webhook (SLACK_WEBHOOK_URL).",
    )
    parser.add_argument(
        "--app-url",
        default=os.getenv("APP_URL", DEFAULT_APP_URL),
        help="Streamlit app URL surfaced as a button in the Slack message.",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Suppress stdout output (useful in CI when --slack is the only sink).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = load_metadata()
    df = load_data()
    today_iso = current_date_iso()
    previous_row = get_latest_previous_row(df, today_iso)
    message = generate_reminder_message(metadata, previous_row, today_iso)

    if not args.no_print:
        print(message)
    if not args.no_save:
        TODAY_REMINDER_PATH.write_text(message, encoding="utf-8")

    if args.slack:
        try:
            slack_notify.post_message(message, link=args.app_url)
            print("[slack] reminder posted", file=sys.stderr)
        except Exception as exc:
            print(f"[slack] failed to post: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
