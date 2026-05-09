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
        .block-container {
            padding-top: 5.9rem;
            padding-bottom: 1rem;
            max-width: 720px;
        }
        h2, h3 {
            font-size: 1rem !important;
            margin-top: 0.8rem !important;
        }
        .app-header {
            position: fixed;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: min(720px, calc(100vw - 1rem));
            z-index: 999;
            margin: 0;
            padding: 0.7rem 0.4rem 0.62rem;
            background: linear-gradient(
                to bottom,
                var(--background-color) 0%,
                var(--background-color) 82%,
                color-mix(in srgb, var(--background-color) 0%, transparent) 100%
            );
            border-bottom: 1px solid rgba(255, 255, 255, 0.26);
        }
        .app-title {
            color: #ffffff !important;
            font-size: 2rem;
            font-weight: 860;
            line-height: 1.08;
            letter-spacing: 0;
            display: block;
            min-height: 2.4rem;
        }
        .date-card {
            display: block;
            margin-top: 0.28rem;
            padding: 0;
            color: #ffffff !important;
            background: transparent;
            border: 0;
            box-shadow: none;
            font-size: 1.08rem;
            font-weight: 820;
        }
        .date-label {
            color: rgba(255, 255, 255, 0.68) !important;
            font-size: 0.9rem;
            font-weight: 760;
            margin-right: 0.5rem;
        }
        div[data-testid="stForm"] {
            border: 1px solid rgba(255, 255, 255, 0.42);
            border-radius: 1.25rem;
            padding: 0.8rem 0.8rem 0.95rem;
            background: color-mix(in srgb, var(--background-color) 86%, var(--secondary-background-color) 14%);
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.12rem;
        }
        div[data-testid="column"] {
            padding-left: 0.12rem !important;
            padding-right: 0.12rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: minmax(8.8rem, 1.05fr) minmax(8.6rem, 1.18fr) minmax(5.4rem, 0.76fr) !important;
            gap: 0.45rem !important;
            align-items: center !important;
            width: 100%;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            flex: none !important;
        }
        div[data-testid="stTextInput"] {
            margin: 0;
        }
        div[data-testid="stNumberInput"] {
            margin: 0;
        }
        div[data-testid="stNumberInput"] > div {
            width: 100%;
        }
        div[data-testid="stNumberInput"] button {
            display: none;
        }
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextInput"] input {
            height: 2.55rem;
            width: 100%;
            padding: 0.25rem 0.72rem;
            font-size: 1.02rem;
            font-weight: 700;
            border: 1px solid #e1e6ee;
            border-radius: 0.85rem;
            color: #111827 !important;
            background: #ffffff !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.8);
        }
        div[data-testid="stNumberInput"] input:focus,
        div[data-testid="stTextInput"] input:focus {
            border-color: #8ab4ff;
            box-shadow: 0 0 0 3px rgba(79, 139, 255, 0.18);
        }
        .field-label {
            min-height: 2.55rem;
            display: flex;
            align-items: center;
            font-size: 1rem;
            font-weight: 760;
            line-height: 1.16;
            color: var(--text-color);
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
            padding: 0.24rem 0.52rem;
            border-radius: 999px;
            color: var(--text-color);
            background: color-mix(in srgb, var(--secondary-background-color) 88%, #7aa7ff 12%);
            border: 1px solid rgba(255, 255, 255, 0.42);
            font-weight: 700;
            font-size: 0.78rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: middle;
        }
        .field-divider {
            border-bottom: 1px solid rgba(255, 255, 255, 0.28);
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
                padding-top: 5.35rem;
                padding-left: 0.35rem;
                padding-right: 0.35rem;
                max-width: 100%;
            }
            .app-header {
                width: 100vw;
                padding: 0.64rem 0.7rem 0.58rem;
            }
            .app-title {
                font-size: 1.72rem;
                min-height: 1.9rem;
            }
            .date-card {
                font-size: 0.98rem;
            }
            .date-label {
                font-size: 0.78rem;
            }
            div[data-testid="stForm"] {
                padding: 0.52rem 0.45rem 0.85rem;
                border-radius: 1rem;
            }
            div[data-testid="stHorizontalBlock"] {
                grid-template-columns: minmax(4.8rem, 0.92fr) minmax(5.2rem, 1.08fr) minmax(3.7rem, 0.68fr) !important;
                gap: 0.18rem !important;
            }
            div[data-testid="stTextInput"] {
                margin: 0;
            }
            div[data-testid="stNumberInput"] input,
            div[data-testid="stTextInput"] input {
                height: 2.25rem;
                font-size: 0.9rem;
                padding-left: 0.42rem;
                padding-right: 0.42rem;
                border-radius: 0.66rem;
            }
            .field-label,
            .field-prev {
                min-height: 2.25rem;
            }
            .field-label {
                font-size: 0.84rem;
                line-height: 1.08;
            }
            .prev-value {
                font-size: 0.66rem;
                padding: 0.13rem 0.25rem;
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
        label_col, input_col, prev_col = st.columns([1.08, 1.34, 0.86], gap="small", vertical_alignment="center")

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

    if field_meta["type"] in {"number", "slider"}:
        step = float(field_meta.get("step") or 1)
        return st.number_input(
            label,
            min_value=float(field_meta["min"]) if field_meta.get("min") is not None else None,
            max_value=float(field_meta["max"]) if field_meta.get("max") is not None else None,
            value=coerce_numeric(default_value, float(field_meta.get("default", 0))),
            step=step,
            format="%.2f" if step < 1 else "%.0f",
            help=help_text,
            label_visibility="collapsed",
            key=field_name,
        )

    return st.text_input(
        label,
        value="" if default_value is None or pd.isna(default_value) else str(default_value),
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
