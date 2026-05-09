from __future__ import annotations

from biometrics_core import LATEST_ANALYSIS_PATH, generate_trend_analysis, load_data, recent_rows_for_prompt


def main() -> None:
    df = load_data()
    recent_rows = recent_rows_for_prompt(df, limit=14)
    analysis = generate_trend_analysis(recent_rows)

    LATEST_ANALYSIS_PATH.write_text(analysis, encoding="utf-8")
    print(f"Saved trend analysis to {LATEST_ANALYSIS_PATH}")


if __name__ == "__main__":
    main()
