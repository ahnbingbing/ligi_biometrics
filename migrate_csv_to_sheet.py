"""One-time migration: load existing CSV (data/biometrics.csv) into Google Sheets.

Behavior:
- Connects to Sheets using sheets_storage's credential resolution.
- Reads local CSV via biometrics_core.load_csv (handles legacy aliases).
- For each row in CSV: inserts into sheet if its date doesn't already exist;
  skips rows whose date is already present.
- Prints a summary.

Run after Sheets credentials and SHEET_ID are configured.
"""

from __future__ import annotations

import sys

import sheets_storage
from biometrics_core import (
    COLUMNS,
    CSV_PATH,
    DATE_COLUMN,
    create_empty_dataframe,
    load_csv,
    load_environment,
    migrate_origin_data,
    normalize_dataframe,
)


def print_connection_diagnostics() -> bool:
    print("Google Sheets connection diagnostics:")
    diagnostics = sheets_storage.diagnose_connection()
    for label, ok, detail in diagnostics:
        status = "OK" if ok else "FAIL"
        print(f"- [{status}] {label}: {detail}")
    return bool(diagnostics and all(ok for _, ok, _ in diagnostics))


def main() -> int:
    load_environment()

    if not print_connection_diagnostics():
        print(
            "\nGoogle Sheets backend is not reachable. Fix the failed step above, then run migration again.",
            file=sys.stderr,
        )
        return 1

    print("")

    if CSV_PATH.exists():
        local_df = load_csv(CSV_PATH)
    else:
        local_df = create_empty_dataframe()
    local_df = migrate_origin_data(local_df)
    local_df = normalize_dataframe(local_df)

    if local_df.empty:
        print("No local rows to migrate.")
        sheets_storage.ensure_header(COLUMNS)
        return 0

    sheet_df = sheets_storage.load_dataframe(COLUMNS)
    existing_dates = set()
    if not sheet_df.empty and DATE_COLUMN in sheet_df.columns:
        existing_dates = {str(d) for d in sheet_df[DATE_COLUMN].dropna().tolist()}

    rows_to_insert = []
    skipped_dates = []
    for _, row in local_df.iterrows():
        date_value = str(row[DATE_COLUMN])
        if date_value in existing_dates:
            skipped_dates.append(date_value)
            continue
        rows_to_insert.append(row.to_dict())

    if not rows_to_insert:
        print(
            f"All {len(local_df)} local rows already exist in the sheet "
            f"(skipped: {', '.join(skipped_dates) or 'none'})."
        )
        return 0

    # Use save_dataframe with the merged dataset to keep the sheet in canonical order.
    import pandas as pd

    new_df = pd.DataFrame(rows_to_insert)
    merged = pd.concat([sheet_df, new_df], ignore_index=True)
    merged = normalize_dataframe(merged)
    sheets_storage.save_dataframe(merged, COLUMNS)

    print(f"Inserted {len(rows_to_insert)} new rows.")
    if skipped_dates:
        print(f"Skipped (already in sheet): {', '.join(skipped_dates)}")
    print(f"Sheet now has {len(merged)} total rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
