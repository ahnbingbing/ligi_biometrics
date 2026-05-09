from __future__ import annotations

import argparse
import os
import sys

from biometrics_core import LATEST_ANALYSIS_PATH, generate_trend_analysis, load_data, recent_rows_for_prompt
import slack_notify


DEFAULT_APP_URL = "https://ligibiometrics.streamlit.app/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate recent Ligi Biometrics trend analysis.")
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print/post the analysis only and do not write data/latest_analysis.md.",
    )
    parser.add_argument(
        "--slack",
        action="store_true",
        help="Post the analysis to the configured Slack webhook (SLACK_WEBHOOK_URL).",
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
    df = load_data()
    recent_rows = recent_rows_for_prompt(df, limit=14)
    analysis = generate_trend_analysis(recent_rows)

    message = f"*Ligi Biometrics 최근 트렌드 분석*\n\n{analysis}"

    if not args.no_print:
        print(message)
    if not args.no_save:
        LATEST_ANALYSIS_PATH.write_text(analysis, encoding="utf-8")
        print(f"Saved trend analysis to {LATEST_ANALYSIS_PATH}", file=sys.stderr)

    if args.slack:
        try:
            slack_notify.post_message(message, link=args.app_url)
            print("[slack] analysis posted", file=sys.stderr)
        except Exception as exc:
            print(f"[slack] failed to post analysis: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
