from __future__ import annotations

import argparse
from datetime import date

from biometrics_core import (
    TODAY_REMINDER_PATH,
    generate_reminder_message,
    get_latest_previous_row,
    load_data,
    load_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate today's Ligi Biometrics check-in reminder.")
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the reminder only and do not write data/today_reminder.txt.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = load_metadata()
    df = load_data()
    today_iso = date.today().isoformat()
    previous_row = get_latest_previous_row(df, today_iso)
    message = generate_reminder_message(metadata, previous_row, today_iso)

    print(message)
    if not args.no_save:
        TODAY_REMINDER_PATH.write_text(message, encoding="utf-8")


if __name__ == "__main__":
    main()
