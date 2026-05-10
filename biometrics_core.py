from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

try:
    import sheets_storage
    SHEETS_STORAGE_IMPORT_ERROR = None
except ImportError as exc:
    sheets_storage = None
    SHEETS_STORAGE_IMPORT_ERROR = exc


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "biometrics.csv"
ORIGIN_CSV_PATH = DATA_DIR / "biometrics_origin.csv"
METADATA_PATH = DATA_DIR / "metadata.json"
TODAY_REMINDER_PATH = DATA_DIR / "today_reminder.txt"
LATEST_ANALYSIS_PATH = DATA_DIR / "latest_analysis.md"

DATE_COLUMN = "date"
FIELD_ORDER = [
    "weight_kg",
    "sleep_quality",
    "sleep_hours",
    "alcohol_intake",
    "salty_carb_heavy_meal",
    "allergy_histamine_score",
    "bowel_status",
    "exercise",
    "non_exercise_kcal",
    "bloating_swelling",
    "gas_distension",
    "stress_level",
    "overall_condition",
    "night_sweat_score",
    "notes",
]
COLUMNS = [DATE_COLUMN, *FIELD_ORDER]

CATEGORIES = {
    "핵심 지표": ["weight_kg", "overall_condition"],
    "수면/회복": ["sleep_quality", "sleep_hours", "night_sweat_score", "stress_level"],
    "식사/알코올": ["alcohol_intake", "salty_carb_heavy_meal"],
    "알레르기/소화": [
        "allergy_histamine_score",
        "bowel_status",
        "bloating_swelling",
        "gas_distension",
    ],
    "운동": ["exercise", "non_exercise_kcal"],
    "메모": ["notes"],
}

LEGACY_COLUMN_ALIASES = {
    "exercise_kcal": "non_exercise_kcal",
}

DAILY_ANALYSIS_SYSTEM_PROMPT = (
    "You are a Korean biometric analysis assistant. You analyze daily body-weight "
    "changes as a dynamic system, not as a simple calorie model. You are not a "
    "doctor and must not diagnose disease. You separate possible causes into "
    "water retention, gut content, gas/distension, alcohol recovery load, sleep "
    "recovery, allergy/histamine response, exercise adaptation, and stress. Be "
    "concise, concrete, and consistent across days."
)

DAILY_ANALYSIS_USER_PROMPT_TEMPLATE = """Analyze today's biometric data.

Rules:
- Answer in Korean.
- Compare today with yesterday.
- Separate bloating/swelling from gas/distension.
- Do not overclaim fat gain from one day of data.
- If alcohol + salty/carb-heavy meal + bloating are high, interpret as likely water/glycogen retention.
- If gas_distension is high, interpret separately as gut fermentation or bowel-state signal.
- If night_sweat_score is high, interpret as possible recovery/discharge signal.
- If allergy_histamine_score is high, consider inflammation/water retention.
- Mention uncertainty clearly.
- End with tomorrow's likely direction.

Input:
TODAY_ROW:
{today_row}

YESTERDAY_ROW:
{yesterday_row}

RECENT_14_ROWS:
{recent_rows}

Output format:
1. 오늘 상태 한 줄 요약
2. 어제 대비 변화
3. 체중 변화의 가능 원인 분해
4. 수분/붓기 vs 장가스 분리
5. 회복 상태
6. 내일 예상 흐름
7. 오늘의 한 가지 조정 포인트
"""

TREND_ANALYSIS_SYSTEM_PROMPT = (
    "You are a Korean biometric trend analysis assistant. You analyze recent "
    "body-weight and recovery data as a dynamic system, not as a simple calorie "
    "model. You are not a doctor and must not diagnose disease. Separate possible "
    "causes into water retention, gut content, gas/distension, alcohol recovery "
    "load, sleep recovery, allergy/histamine response, exercise adaptation, and "
    "stress. Be concise, concrete, and consistent."
)

TREND_ANALYSIS_USER_PROMPT_TEMPLATE = """Analyze recent biometric trend data.

Rules:
- Answer in Korean.
- Focus on recent direction, repeated patterns, and likely drivers.
- Separate bloating/swelling from gas/distension.
- Do not overclaim fat gain or fat loss from short-term weight movement.
- Mention uncertainty clearly.
- Give practical next-step guidance.

Input:
RECENT_ROWS:
{recent_rows}

Output format:
1. 최근 흐름 요약
2. 체중 변동 패턴
3. 반복되는 가능 원인
4. 수분/붓기 vs 장가스 분리
5. 회복/스트레스/운동 적응
6. 다음 2-3일 관찰 포인트
7. 한 가지 우선 조정
"""

TREND_REPORT_USER_PROMPT_TEMPLATE = """Analyze recent biometric trend data after today's check-in.

Rules:
- Answer in Korean.
- Return JSON only. Do not wrap it in markdown fences.
- `summary_lines` must contain exactly 3 short lines suitable for a Slack main message.
- `full_analysis` can be longer, but keep it practical and concise.
- In `full_analysis`, focus on recent direction, repeated patterns, and likely drivers.
- Separate bloating/swelling from gas/distension.
- Do not overclaim fat gain or fat loss from short-term weight movement.
- Mention uncertainty clearly.

Input:
TODAY_ROW:
{today_row}

RECENT_ROWS:
{recent_rows}

Output JSON schema:
{{
  "summary_lines": ["line 1", "line 2", "line 3"],
  "full_analysis": "markdown analysis"
}}
"""


def load_metadata() -> dict[str, dict[str, Any]]:
    with METADATA_PATH.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    missing = [field for field in FIELD_ORDER if field not in metadata]
    if missing:
        raise ValueError(f"metadata.json is missing fields: {', '.join(missing)}")
    return metadata


def create_empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for old_column, new_column in LEGACY_COLUMN_ALIASES.items():
        if old_column in df.columns and new_column not in df.columns:
            df[new_column] = df[old_column]

    for column in COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    normalized = df[COLUMNS].copy()
    if normalized.empty:
        return normalized

    normalized[DATE_COLUMN] = pd.to_datetime(normalized[DATE_COLUMN], errors="coerce").dt.date.astype(str)
    normalized = normalized.dropna(subset=[DATE_COLUMN])
    normalized = normalized[normalized[DATE_COLUMN] != "NaT"]
    return normalized.sort_values(DATE_COLUMN).drop_duplicates(subset=[DATE_COLUMN], keep="last").reset_index(drop=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return create_empty_dataframe()
    return normalize_dataframe(pd.read_csv(path))


def load_environment() -> None:
    load_dotenv(BASE_DIR / ".env")


def sheets_storage_enabled() -> bool:
    if sheets_storage is None:
        return False
    load_environment()
    return sheets_storage.storage_available()


def load_sheets_dataframe() -> pd.DataFrame | None:
    if not sheets_storage_enabled():
        return None
    try:
        df = sheets_storage.load_dataframe(COLUMNS)
    except Exception:
        return None
    return normalize_dataframe(df)


def save_sheets_dataframe(df: pd.DataFrame) -> bool:
    if not sheets_storage_enabled():
        return False
    try:
        sheets_storage.save_dataframe(df, COLUMNS)
        return True
    except Exception:
        return False


def diagnose_sheets_connection() -> list[tuple[str, bool, str]]:
    if sheets_storage is None:
        detail = str(SHEETS_STORAGE_IMPORT_ERROR) if SHEETS_STORAGE_IMPORT_ERROR else "unknown import error"
        return [("Sheets module", False, f"sheets_storage.py could not be imported: {detail}")]
    load_environment()
    return sheets_storage.diagnose_connection()


def migrate_origin_data(df: pd.DataFrame) -> pd.DataFrame:
    if not ORIGIN_CSV_PATH.exists():
        return df

    origin_df = load_csv(ORIGIN_CSV_PATH)
    if origin_df.empty:
        return df
    if df.empty:
        return origin_df

    merged = pd.concat([origin_df, df], ignore_index=True)
    return normalize_dataframe(merged)


def load_data() -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sheets_df = load_sheets_dataframe()
    if sheets_df is not None:
        return sheets_df

    if not CSV_PATH.exists():
        return migrate_origin_data(create_empty_dataframe())

    return migrate_origin_data(load_csv(CSV_PATH))


def save_data(df: pd.DataFrame) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = normalize_dataframe(df)
    output.to_csv(CSV_PATH, index=False)
    return save_sheets_dataframe(output)


def clean_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    cleaned = {}
    for key, value in row.items():
        cleaned[key] = None if pd.isna(value) else value
    return cleaned


def get_today_row(df: pd.DataFrame, today_iso: str) -> dict[str, Any] | None:
    if df.empty:
        return None
    matches = df[df[DATE_COLUMN] == today_iso]
    if matches.empty:
        return None
    return matches.iloc[-1].to_dict()


def get_latest_previous_row(df: pd.DataFrame, today_iso: str | None = None) -> dict[str, Any] | None:
    if df.empty:
        return None
    if today_iso is None:
        previous = df.sort_values(DATE_COLUMN)
    else:
        previous = df[df[DATE_COLUMN] < today_iso].sort_values(DATE_COLUMN)
    if previous.empty:
        return None
    return previous.iloc[-1].to_dict()


def default_for_field(
    field_name: str,
    field_meta: dict[str, Any],
    today_row: dict[str, Any] | None,
    yesterday_row: dict[str, Any] | None,
) -> Any:
    for source in (today_row, yesterday_row):
        if source and field_name in source and not pd.isna(source[field_name]):
            return source[field_name]
    return field_meta.get("default")


def upsert_today(df: pd.DataFrame, today_iso: str, row: dict[str, Any]) -> pd.DataFrame:
    row_with_date = {DATE_COLUMN: today_iso, **row}
    if df.empty or today_iso not in set(df[DATE_COLUMN].astype(str)):
        return normalize_dataframe(pd.concat([df, pd.DataFrame([row_with_date])], ignore_index=True))

    updated = df.copy().astype("object")
    mask = updated[DATE_COLUMN].astype(str) == today_iso
    for column, value in row_with_date.items():
        updated.loc[mask, column] = value
    return normalize_dataframe(updated)


def rows_for_prompt(df: pd.DataFrame, today_iso: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    sorted_df = df.sort_values(DATE_COLUMN).reset_index(drop=True)
    today_row = clean_row(get_today_row(sorted_df, today_iso))
    yesterday_row = clean_row(get_latest_previous_row(sorted_df, today_iso))
    recent_rows = [clean_row(row) for row in sorted_df.tail(14).to_dict(orient="records")]
    return today_row, yesterday_row, recent_rows


def recent_rows_for_prompt(df: pd.DataFrame, limit: int = 14) -> list[dict[str, Any]]:
    sorted_df = df.sort_values(DATE_COLUMN).reset_index(drop=True)
    return [clean_row(row) for row in sorted_df.tail(limit).to_dict(orient="records")]


def openai_client() -> OpenAI | None:
    load_environment()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_analysis(
    today_row: dict[str, Any],
    yesterday_row: dict[str, Any],
    recent_rows: list[dict[str, Any]],
) -> str:
    client = openai_client()
    if client is None:
        return "OPENAI_API_KEY가 .env에 설정되어 있지 않아 분석을 생성하지 못했습니다."

    user_prompt = DAILY_ANALYSIS_USER_PROMPT_TEMPLATE.format(
        today_row=json.dumps(today_row, ensure_ascii=False, indent=2),
        yesterday_row=json.dumps(yesterday_row, ensure_ascii=False, indent=2),
        recent_rows=json.dumps(recent_rows, ensure_ascii=False, indent=2),
    )
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0.3,
            input=[
                {"role": "system", "content": DAILY_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text
    except Exception as exc:
        return format_openai_error(exc)


def generate_trend_analysis(recent_rows: list[dict[str, Any]]) -> str:
    client = openai_client()
    if client is None:
        return "OPENAI_API_KEY가 .env에 설정되어 있지 않아 트렌드 분석을 생성하지 못했습니다."

    user_prompt = TREND_ANALYSIS_USER_PROMPT_TEMPLATE.format(
        recent_rows=json.dumps(recent_rows, ensure_ascii=False, indent=2)
    )
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0.3,
            input=[
                {"role": "system", "content": TREND_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text
    except Exception as exc:
        return format_openai_error(exc)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _fallback_summary_lines(text: str) -> list[str]:
    lines = [
        line.strip(" -")
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    summary_lines = lines[:3]
    while len(summary_lines) < 3:
        summary_lines.append("오늘 기록을 반영한 최근 흐름 분석을 확인해 주세요.")
    return summary_lines


def generate_trend_report(
    today_row: dict[str, Any],
    recent_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    client = openai_client()
    if client is None:
        message = "OPENAI_API_KEY가 .env에 설정되어 있지 않아 트렌드 분석을 생성하지 못했습니다."
        return {"summary_lines": _fallback_summary_lines(message), "full_analysis": message}

    user_prompt = TREND_REPORT_USER_PROMPT_TEMPLATE.format(
        today_row=json.dumps(today_row, ensure_ascii=False, indent=2),
        recent_rows=json.dumps(recent_rows, ensure_ascii=False, indent=2),
    )
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0.3,
            input=[
                {"role": "system", "content": TREND_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_text = response.output_text
        try:
            parsed = json.loads(_strip_json_fence(raw_text))
        except json.JSONDecodeError:
            return {"summary_lines": _fallback_summary_lines(raw_text), "full_analysis": raw_text}
        summary_lines = parsed.get("summary_lines") or _fallback_summary_lines(raw_text)
        summary_lines = [str(line).strip() for line in summary_lines if str(line).strip()][:3]
        while len(summary_lines) < 3:
            summary_lines.append("오늘 기록을 반영한 최근 흐름 분석을 확인해 주세요.")
        full_analysis = str(parsed.get("full_analysis") or raw_text).strip()
        return {"summary_lines": summary_lines, "full_analysis": full_analysis}
    except Exception as exc:
        message = format_openai_error(exc)
        return {"summary_lines": _fallback_summary_lines(message), "full_analysis": message}


def format_openai_error(exc: Exception) -> str:
    message = str(exc)
    if "insufficient_quota" in message or "exceeded your current quota" in message:
        return (
            "OpenAI API 할당량 또는 결제 한도 때문에 분석을 생성하지 못했습니다.\n\n"
            "- 저장된 생체 데이터는 정상적으로 저장되었습니다.\n"
            "- OpenAI dashboard에서 billing/usage limit을 확인하거나 API key를 교체한 뒤 다시 분석해 주세요."
        )
    if "rate_limit" in message or "429" in message:
        return (
            "OpenAI API 요청 한도에 걸려 분석을 생성하지 못했습니다.\n\n"
            "잠시 후 다시 시도해 주세요. 저장된 생체 데이터는 정상적으로 저장되었습니다."
        )
    return f"OpenAI 분석 생성 중 오류가 발생했습니다: {message}"


def format_value(value: Any, unit: str = "") -> str:
    if value is None or pd.isna(value):
        return "기록 없음"
    suffix = f" {unit}" if unit else ""
    return f"{value}{suffix}"


def field_scale_text(field_meta: dict[str, Any]) -> str:
    field_type = field_meta.get("type")
    if field_type == "text":
        return "자유 입력"

    min_value = field_meta.get("min")
    max_value = field_meta.get("max")
    step = field_meta.get("step")
    unit = field_meta.get("unit", "")
    unit_suffix = f" {unit}" if unit else ""
    if min_value is None or max_value is None:
        return f"단위: {unit}" if unit else "숫자 입력"
    return f"{min_value}~{max_value}{unit_suffix}, step {step}"


def generate_reminder_message(
    metadata: dict[str, dict[str, Any]],
    previous_row: dict[str, Any] | None,
    today_iso: str | None = None,
) -> str:
    return "오늘도 기록하러 가볼까요?"
