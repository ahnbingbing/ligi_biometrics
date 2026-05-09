from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from biometrics_core import (
    DATE_COLUMN,
    FIELD_ORDER,
    default_for_field,
    generate_analysis,
    get_latest_previous_row,
    get_today_row,
    load_data,
    load_metadata,
    rows_for_prompt,
    save_data,
    upsert_today,
)


def apply_compact_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ligi-bg: #f5f5f7;
            --ligi-card: #ffffff;
            --ligi-text: #1d1d1f;
            --ligi-title: #000000;
            --ligi-secondary: #8e8e93;
            --ligi-prev: #3a3a3c;
            --ligi-divider: #e5e5ea;
            --ligi-input-bg: #ffffff;
            --ligi-input-text: #111827;
            --ligi-input-border: #d1d5db;
            --ligi-input-focus: #8f98a3;
            --ligi-shadow: rgba(0, 0, 0, 0.06);
            --ligi-input-inner: #f2f2f7;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --ligi-bg: #000000;
                --ligi-card: #1c1c1e;
                --ligi-text: #f5f5f7;
                --ligi-title: #ffffff;
                --ligi-secondary: #8e8e93;
                --ligi-prev: #d1d1d6;
                --ligi-divider: #38383a;
                --ligi-input-bg: #ffffff;
                --ligi-input-text: #111827;
                --ligi-input-border: #636366;
                --ligi-input-focus: #8e8e93;
                --ligi-shadow: rgba(0, 0, 0, 0.26);
                --ligi-input-inner: #e5e5ea;
            }
        }
        .stApp {
            background: var(--ligi-bg);
            color: var(--ligi-text);
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        .block-container {
            padding-top: clamp(1.2rem, 4vh, 2.6rem);
            padding-bottom: 1.25rem;
            max-width: min(92vw, 720px);
        }
        h2, h3 {
            font-size: 1rem !important;
            margin-top: 0.8rem !important;
        }
        .app-header {
            margin: 0 0 1.1rem;
            padding: 0;
            background: transparent;
            border: 0;
        }
        .app-title {
            color: var(--ligi-title) !important;
            font-size: clamp(2.2rem, 5vw, 3.1rem);
            font-weight: 860;
            line-height: 1.08;
            letter-spacing: 0;
            display: block;
            min-height: auto;
        }
        .date-card {
            display: block;
            margin-top: 0.45rem;
            padding: 0;
            color: var(--ligi-text) !important;
            background: transparent;
            border: 0;
            box-shadow: none;
            font-size: clamp(1.05rem, 2vw, 1.25rem);
            font-weight: 820;
        }
        .date-label {
            color: var(--ligi-secondary) !important;
            font-size: clamp(0.8rem, 1.5vw, 0.95rem);
            font-weight: 760;
            margin-right: 0.5rem;
        }
        div[data-testid="stForm"] {
            border: 0;
            border-radius: 1.35rem;
            padding: clamp(0.68rem, 1.4vw, 1rem);
            background: var(--ligi-card);
            box-shadow: 0 18px 44px var(--ligi-shadow);
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.12rem;
        }
        div[data-testid="column"] {
            padding-left: 0.12rem !important;
            padding-right: 0.12rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: clamp(0.12rem, 1vw, 0.45rem) !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 0 !important;
        }
        div[data-testid="stTextInput"] {
            margin: 0;
        }
        div[data-testid="stTextInput"] input {
            height: 2.55rem;
            width: 100%;
            padding: 0.25rem 0.62rem;
            font-size: clamp(1rem, 1.5vw, 1.12rem);
            font-weight: 700;
            border: 2px solid var(--ligi-input-border);
            border-radius: 0.85rem;
            color: var(--ligi-input-text) !important;
            background: var(--ligi-input-bg) !important;
            box-shadow: inset 0 0 0 1px var(--ligi-input-inner);
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: var(--ligi-input-focus);
            box-shadow: 0 0 0 2px rgba(142, 142, 147, 0.18);
        }
        .field-label {
            min-height: 2.55rem;
            display: flex;
            align-items: center;
            font-size: clamp(1rem, 1.8vw, 1.18rem);
            font-weight: 760;
            line-height: 1.16;
            color: var(--ligi-text);
            word-break: keep-all;
        }
        .field-prev {
            min-height: 2.55rem;
            display: flex;
            align-items: center;
            min-width: 0;
        }
        .prev-value {
            display: inline-block;
            max-width: 100%;
            padding: 0.2rem 0.25rem;
            border-radius: 999px;
            color: var(--ligi-prev);
            background: transparent;
            border: 0;
            font-weight: 700;
            font-size: clamp(0.78rem, 1.45vw, 0.98rem);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: middle;
        }
        .field-divider {
            border-bottom: 1px solid var(--ligi-divider);
            margin: 0.04rem 0;
        }
        div[data-testid="stFormSubmitButton"] {
            margin-top: 1rem;
        }
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 0.85rem;
        }
        @media (max-width: 640px) {
            .block-container {
                padding-top: max(1.1rem, env(safe-area-inset-top));
                padding-left: 0;
                padding-right: 0;
                max-width: min(94vw, 390px);
            }
            .app-header {
                margin-bottom: 0.9rem;
            }
            .app-title {
                font-size: clamp(2rem, 8vw, 2.45rem);
            }
            .date-card {
                font-size: clamp(1rem, 4vw, 1.12rem);
            }
            .date-label {
                font-size: clamp(0.72rem, 3.2vw, 0.88rem);
            }
            div[data-testid="stForm"] {
                padding: 0.58rem 0.62rem;
                border-radius: 1.25rem;
            }
            div[data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: minmax(0, 1.42fr) minmax(0, 0.72fr) minmax(0, 0.86fr) !important;
                gap: clamp(0.08rem, 1vw, 0.16rem) !important;
                align-items: center !important;
                width: 100%;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
                width: auto !important;
                flex: none !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
                width: auto !important;
                flex: none !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
                width: auto !important;
                flex: none !important;
            }
            div[data-testid="stTextInput"] {
                margin: 0;
            }
            div[data-testid="stTextInput"] input {
                height: 2.4rem;
                font-size: clamp(0.92rem, 3.8vw, 1.04rem);
                padding-left: 0.34rem;
                padding-right: 0.34rem;
                border-radius: 0.62rem;
                border-width: 2px;
            }
            .field-label,
            .field-prev {
                min-height: 2.4rem;
            }
            .field-label {
                font-size: clamp(0.9rem, 3.9vw, 1.04rem);
                line-height: 1.06;
            }
            .prev-value {
                font-size: clamp(0.6rem, 3vw, 0.78rem);
                padding: 0.13rem 0.22rem;
            }
            .field-divider {
                margin: 0.02rem 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(today_iso: str) -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-title">Ligi Biometrics</div>
            <div class="date-card"><span class="date-label">오늘</span>{today_iso}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def install_input_select_script() -> None:
    components.html(
        """
        <script>
        const attachSelectOnFocus = () => {
            const doc = window.parent.document;
            doc.querySelectorAll('input').forEach((input) => {
                if (input.dataset.ligiSelectAttached === 'true') return;
                input.dataset.ligiSelectAttached = 'true';
                input.addEventListener('focus', () => {
                    window.setTimeout(() => input.select(), 0);
                });
                input.addEventListener('mouseup', (event) => {
                    event.preventDefault();
                });
            });
        };
        attachSelectOnFocus();
        window.setInterval(attachSelectOnFocus, 1000);
        </script>
        """,
        height=0,
    )


def coerce_numeric(value: Any, fallback: float) -> float:
    try:
        if pd.isna(value):
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def previous_value_text(
    field_name: str,
    field_meta: dict[str, Any],
    yesterday_row: dict[str, Any] | None,
) -> str:
    unit = field_meta.get("unit", "")
    yesterday_value = None if not yesterday_row else yesterday_row.get(field_name)
    previous_text = "이전 기록 없음" if yesterday_value is None or pd.isna(yesterday_value) else yesterday_value
    unit_suffix = f" {unit}" if unit else ""
    return f"{previous_text}{unit_suffix}"


def render_form_fields(
    metadata: dict[str, dict[str, Any]],
    today_row: dict[str, Any] | None,
    yesterday_row: dict[str, Any] | None,
) -> dict[str, Any]:
    submitted_values: dict[str, Any] = {}

    for field_name in FIELD_ORDER:
        field_meta = metadata[field_name]
        default_value = default_for_field(field_name, field_meta, today_row, yesterday_row)
        previous_text = previous_value_text(field_name, field_meta, yesterday_row)
        label_col, input_col, prev_col = st.columns([1.62, 0.72, 0.98], gap="small", vertical_alignment="center")

        with label_col:
            st.markdown(f"<div class='field-label'>{field_meta['label_ko']}</div>", unsafe_allow_html=True)

        with input_col:
            submitted_values[field_name] = render_input(field_name, field_meta, default_value)

        with prev_col:
            st.markdown(
                f"<div class='field-prev'><span class='prev-value'>{previous_text}</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div class='field-divider'></div>", unsafe_allow_html=True)

    return submitted_values


def render_input(field_name: str, field_meta: dict[str, Any], default_value: Any) -> Any:
    label = field_meta["label_ko"]
    help_text = field_meta.get("anchor_ko", "")

    return st.text_input(
        label,
        value=format_default_value(default_value, field_meta),
        help=help_text,
        label_visibility="collapsed",
        key=field_name,
    )


def format_default_value(value: Any, field_meta: dict[str, Any]) -> str:
    if value is None or pd.isna(value):
        return ""
    if field_meta["type"] not in {"number", "slider"}:
        return str(value)

    numeric_value = coerce_numeric(value, float(field_meta.get("default", 0)))
    step = float(field_meta.get("step") or 1)
    if step < 1:
        return f"{numeric_value:.2f}"
    return str(int(numeric_value)) if numeric_value.is_integer() else str(numeric_value)


def normalize_submitted_values(
    values: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field_name, value in values.items():
        field_meta = metadata[field_name]
        if field_meta["type"] not in {"number", "slider"}:
            normalized[field_name] = value
            continue

        fallback = coerce_numeric(field_meta.get("default"), 0)
        numeric_value = coerce_numeric(value, fallback)
        min_value = field_meta.get("min")
        max_value = field_meta.get("max")
        if min_value is not None:
            numeric_value = max(float(min_value), numeric_value)
        if max_value is not None:
            numeric_value = min(float(max_value), numeric_value)
        normalized[field_name] = numeric_value
    return normalized


def render_charts(df: pd.DataFrame) -> None:
    if df.empty:
        return

    chart_df = df.copy()
    chart_df[DATE_COLUMN] = pd.to_datetime(chart_df[DATE_COLUMN], errors="coerce")
    chart_df = chart_df.dropna(subset=[DATE_COLUMN]).set_index(DATE_COLUMN).sort_index()
    if chart_df.empty:
        return

    numeric_columns = ["weight_kg", "bloating_swelling", "gas_distension"]
    for column in numeric_columns:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")

    st.subheader("추세")
    if chart_df["weight_kg"].notna().any():
        st.line_chart(chart_df[["weight_kg"]], height=220)
    if chart_df[["bloating_swelling", "gas_distension"]].notna().any().any():
        st.line_chart(chart_df[["bloating_swelling", "gas_distension"]], height=220)


def main() -> None:
    st.set_page_config(page_title="Ligi Biometrics", page_icon="LB", layout="wide")
    apply_compact_styles()
    install_input_select_script()

    metadata = load_metadata()
    df = load_data()
    today_iso = date.today().isoformat()
    today_row = get_today_row(df, today_iso)
    yesterday_row = get_latest_previous_row(df, today_iso)

    render_header(today_iso)

    with st.form("biometrics_form"):
        submitted_values = render_form_fields(metadata, today_row, yesterday_row)
        submitted = st.form_submit_button("저장하고 분석하기", type="primary")

    if submitted:
        normalized_values = normalize_submitted_values(submitted_values, metadata)
        updated_df = upsert_today(df, today_iso, normalized_values)
        save_data(updated_df)
        st.success("오늘 기록을 저장했습니다.")

        prompt_today, prompt_yesterday, prompt_recent = rows_for_prompt(updated_df, today_iso)
        with st.spinner("한국어 분석을 생성하는 중입니다..."):
            try:
                analysis = generate_analysis(prompt_today, prompt_yesterday, prompt_recent)
            except Exception as exc:
                analysis = f"분석 생성 중 오류가 발생했습니다: {exc}"
        st.subheader("오늘의 분석")
        st.markdown(analysis)
        df = updated_df

    with st.expander("Appendix: 추세", expanded=False):
        render_charts(df)

    with st.expander("Appendix: 최근 14일 데이터", expanded=False):
        st.dataframe(df.sort_values(DATE_COLUMN, ascending=False).head(14), use_container_width=True)


if __name__ == "__main__":
    main()
