"""Google Sheets storage backend for Ligi Biometrics.

Resolves credentials from (in order):
1. Streamlit secrets (`st.secrets["gcp_service_account"]`) — for Streamlit Cloud
2. Environment variable `GOOGLE_SHEETS_CREDS` containing the JSON string — for GitHub Actions
3. Environment variable `GOOGLE_APPLICATION_CREDENTIALS` pointing to a JSON file — for local dev

Sheet ID resolves from:
1. `st.secrets["sheet_id"]`
2. Env var `SHEET_ID`

Worksheet name defaults to "Sheet1" (override with `worksheet_name` / `WORKSHEET_NAME`).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import gspread
import pandas as pd
from gspread.exceptions import APIError, SpreadsheetNotFound
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_WORKSHEET_NAME = "Sheet1"


def _mask(value: str | None, visible: int = 6) -> str:
    if not value:
        return "not set"
    if len(value) <= visible * 2:
        return "<set>"
    return f"{value[:visible]}...{value[-visible:]}"


def _streamlit_secret(key: str) -> Any:
    """Return st.secrets[key] if available, else None.

    Returns None if Streamlit isn't installed, no secrets.toml is configured,
    or the key is absent. Catches all exceptions because Streamlit's secrets
    accessors raise different error types across versions.
    """
    try:
        import streamlit as st  # type: ignore
    except ImportError:
        return None
    try:
        return st.secrets[key]
    except Exception:
        return None


def _load_credentials() -> Credentials:
    gcp = _streamlit_secret("gcp_service_account")
    if gcp:
        info = dict(gcp)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    creds_json = os.getenv("GOOGLE_SHEETS_CREDS")
    if creds_json:
        info = json.loads(creds_json)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    raise RuntimeError(
        "No Google Sheets credentials found. Set st.secrets[gcp_service_account], "
        "GOOGLE_SHEETS_CREDS env var, or GOOGLE_APPLICATION_CREDENTIALS env var."
    )


def credential_source() -> str:
    if _streamlit_secret("gcp_service_account"):
        return "streamlit secrets: gcp_service_account"
    if os.getenv("GOOGLE_SHEETS_CREDS"):
        return "env: GOOGLE_SHEETS_CREDS"
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        return f"env: GOOGLE_APPLICATION_CREDENTIALS={creds_path}"
    return "not configured"


def _resolve_setting(key: str, env_var: str, default: str | None = None) -> str | None:
    value = _streamlit_secret(key)
    if value:
        return str(value)
    return os.getenv(env_var, default)


def get_sheet_id() -> str:
    sheet_id = _resolve_setting("sheet_id", "SHEET_ID")
    if not sheet_id:
        raise RuntimeError("SHEET_ID not configured (set in st.secrets or env).")
    return sheet_id


def get_worksheet_name() -> str:
    name = _resolve_setting("worksheet_name", "WORKSHEET_NAME", DEFAULT_WORKSHEET_NAME)
    return name or DEFAULT_WORKSHEET_NAME


@lru_cache(maxsize=1)
def _client() -> gspread.Client:
    creds = _load_credentials()
    return gspread.authorize(creds)


def _worksheet() -> gspread.Worksheet:
    client = _client()
    sheet = client.open_by_key(get_sheet_id())
    name = get_worksheet_name()
    try:
        return sheet.worksheet(name)
    except gspread.WorksheetNotFound:
        return sheet.add_worksheet(title=name, rows=1000, cols=26)


def storage_available() -> bool:
    """Return True if Sheets backend is reachable. Used by the app to decide
    whether to fall back to local CSV-only mode for development.
    """
    try:
        _ = _worksheet()
        return True
    except Exception:
        return False


def diagnose_connection() -> list[tuple[str, bool, str]]:
    """Return step-by-step Sheets connection diagnostics for CLI scripts."""
    results: list[tuple[str, bool, str]] = []

    sheet_id = _resolve_setting("sheet_id", "SHEET_ID")
    worksheet_name = _resolve_setting("worksheet_name", "WORKSHEET_NAME", DEFAULT_WORKSHEET_NAME)
    results.append(("SHEET_ID", bool(sheet_id), _mask(sheet_id)))
    results.append(("WORKSHEET_NAME", bool(worksheet_name), worksheet_name or "not set"))

    source = credential_source()
    source_ok = source != "not configured"
    if source.startswith("env: GOOGLE_APPLICATION_CREDENTIALS="):
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        source_ok = bool(creds_path and os.path.exists(creds_path))
        detail = f"{creds_path} ({'exists' if source_ok else 'file not found'})"
    else:
        detail = source
    results.append(("Credentials source", source_ok, detail))

    try:
        creds = _load_credentials()
        service_email = getattr(creds, "service_account_email", None)
        results.append(("Credentials parse", True, service_email or "loaded"))
    except Exception as exc:
        results.append(("Credentials parse", False, f"{type(exc).__name__}: {exc}"))
        return results

    try:
        client = gspread.authorize(creds)
        results.append(("Google auth", True, "authorized"))
    except Exception as exc:
        results.append(("Google auth", False, f"{type(exc).__name__}: {exc}"))
        return results

    try:
        sheet = client.open_by_key(get_sheet_id())
        results.append(("Open spreadsheet", True, sheet.title))
    except SpreadsheetNotFound as exc:
        results.append(
            (
                "Open spreadsheet",
                False,
                (
                    "SpreadsheetNotFound: check SHEET_ID and share the sheet with "
                    f"{getattr(creds, 'service_account_email', 'the service account')}"
                ),
            )
        )
        return results
    except APIError as exc:
        results.append(("Open spreadsheet", False, f"APIError: {exc}"))
        return results
    except Exception as exc:
        results.append(("Open spreadsheet", False, f"{type(exc).__name__}: {exc}"))
        return results

    try:
        ws = sheet.worksheet(get_worksheet_name())
        results.append(("Open worksheet", True, ws.title))
    except gspread.WorksheetNotFound:
        results.append(("Open worksheet", True, f"{get_worksheet_name()} not found; will be created"))
    except Exception as exc:
        results.append(("Open worksheet", False, f"{type(exc).__name__}: {exc}"))

    return results


def ensure_header(columns: list[str]) -> None:
    """Make sure the first row of the sheet matches `columns`. If the sheet is
    empty, write the header. If header exists but differs, leave it alone (the
    user may have manually reordered) — the caller should align to actual header.
    """
    ws = _worksheet()
    existing = ws.row_values(1)
    if not existing:
        ws.update("A1", [columns])
        return


def load_dataframe(columns: list[str]) -> pd.DataFrame:
    """Read all rows from the sheet into a DataFrame with the given column order.

    Missing columns are added as NA. Extra columns in the sheet are dropped.
    """
    ws = _worksheet()
    records = ws.get_all_records(default_blank=None)
    if not records:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(records)
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def _sanitize_row_value(value: Any) -> Any:
    """Convert pandas/numpy values into types the Sheets API accepts."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if pd.isna(value):
        return ""
    return value


def save_dataframe(df: pd.DataFrame, columns: list[str]) -> None:
    """Replace the entire worksheet contents with the given DataFrame.

    Uses a single batch update for atomicity and quota friendliness.
    """
    ws = _worksheet()
    ordered = df.copy()
    for col in columns:
        if col not in ordered.columns:
            ordered[col] = pd.NA
    ordered = ordered[columns]

    rows: list[list[Any]] = [columns]
    for _, row in ordered.iterrows():
        rows.append([_sanitize_row_value(row[col]) for col in columns])

    ws.clear()
    ws.update("A1", rows, value_input_option="USER_ENTERED")


def upsert_row(date_value: str, row: dict[str, Any], columns: list[str]) -> None:
    """Insert or update a single row identified by `date_value` in the date column.

    Avoids rewriting the whole sheet when only one date changes.
    """
    ws = _worksheet()
    existing = ws.get_all_records(default_blank=None)
    header = ws.row_values(1)
    if not header:
        ensure_header(columns)
        header = columns

    target_row_index = None  # 1-based row index in the sheet
    for idx, record in enumerate(existing, start=2):
        if str(record.get("date", "")) == date_value:
            target_row_index = idx
            break

    full_row = {col: _sanitize_row_value(row.get(col, "")) for col in header}
    full_row["date"] = date_value
    values = [full_row.get(col, "") for col in header]

    if target_row_index is None:
        ws.append_row(values, value_input_option="USER_ENTERED")
    else:
        end_col_letter = gspread.utils.rowcol_to_a1(1, len(header))[:-1]
        ws.update(
            f"A{target_row_index}:{end_col_letter}{target_row_index}",
            [values],
            value_input_option="USER_ENTERED",
        )
