from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from biometrics_core import (
    CAUSE_FIELD_ORDER,
    DATE_COLUMN,
    FIELD_ORDER,
    RESULT_FIELD_ORDER,
    current_date_iso,
    diagnose_sheets_connection,
    generate_trend_report,
    get_latest_previous_row,
    get_today_row,
    load_data,
    load_metadata,
    rows_for_prompt,
    save_data,
    upsert_today,
)
import slack_notify


DEFAULT_APP_URL = "https://ligibiometrics.streamlit.app/"
CAUSE_DRAFT_KEY = "cause_values"
PAGE_KEY = "entry_page"


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
        .section-title {
            color: var(--ligi-title);
            font-size: clamp(1.25rem, 2.6vw, 1.65rem);
            font-weight: 840;
            line-height: 1.18;
            margin: 0 0 clamp(1.05rem, 2.2vw, 1.45rem);
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
        const textInputLabels = new Set(['운동']);
        const attachSelectOnFocus = () => {
            const doc = window.parent.document;
            doc.querySelectorAll('div[data-testid="stTextInput"] input').forEach((input) => {
                const label = input.getAttribute('aria-label') || '';
                if (!textInputLabels.has(label)) {
                    input.inputMode = 'decimal';
                    input.pattern = '[0-9]*[.,]?[0-9]*';
                    input.autocomplete = 'off';
                } else {
                    input.inputMode = 'text';
                    input.removeAttribute('pattern');
                }
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


def stored_or_default_value(
    field_name: str,
    field_meta: dict[str, Any],
    stored_row: dict[str, Any] | None,
) -> Any:
    if stored_row and field_name in stored_row and not pd.isna(stored_row[field_name]):
        return stored_row[field_name]
    return field_meta.get("default")


def render_form_fields(
    metadata: dict[str, dict[str, Any]],
    field_order: list[str],
    stored_row: dict[str, Any] | None,
    previous_row: dict[str, Any] | None,
    key_prefix: str,
) -> dict[str, Any]:
    submitted_values: dict[str, Any] = {}

    for field_name in field_order:
        field_meta = metadata[field_name]
        default_value = stored_or_default_value(field_name, field_meta, stored_row)
        previous_text = previous_value_text(field_name, field_meta, previous_row)
        label_col, input_col, prev_col = st.columns([1.62, 0.72, 0.98], gap="small", vertical_alignment="center")

        with label_col:
            st.markdown(f"<div class='field-label'>{field_meta['label_ko']}</div>", unsafe_allow_html=True)

        with input_col:
            submitted_values[field_name] = render_input(field_name, field_meta, default_value, key_prefix)

        with prev_col:
            st.markdown(
                f"<div class='field-prev'><span class='prev-value'>{previous_text}</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div class='field-divider'></div>", unsafe_allow_html=True)

    return submitted_values


def render_input(field_name: str, field_meta: dict[str, Any], default_value: Any, key_prefix: str) -> Any:
    label = field_meta["label_ko"]
    help_text = field_meta.get("anchor_ko", "")

    return st.text_input(
        label,
        value=format_default_value(default_value, field_meta),
        help=help_text,
        label_visibility="collapsed",
        key=f"{key_prefix}_{field_name}",
    )


def format_default_value(value: Any, field_meta: dict[str, Any]) -> str:
    if value is None or pd.isna(value):
        return ""
    if field_meta["type"] not in {"number", "slider", "score"}:
        return str(value)

    numeric_value = coerce_numeric(value, float(field_meta.get("default", 0)))
    return f"{numeric_value:.1f}"


def normalize_submitted_values(
    values: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field_name, value in values.items():
        field_meta = metadata[field_name]
        if field_meta["type"] not in {"number", "slider", "score"}:
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
        normalized[field_name] = round(numeric_value, 1)
    return normalized


def today_values_text(today_row: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> str:
    lines = ["*오늘 입력값*"]
    for title, field_order in (("전날 원인", CAUSE_FIELD_ORDER), ("오늘 결과", RESULT_FIELD_ORDER)):
        lines.append(f"*{title}*")
        for field_name in field_order:
            field_meta = metadata[field_name]
            label = field_meta["label_ko"]
            unit = field_meta.get("unit", "")
            value = today_row.get(field_name)
            if value is None or pd.isna(value):
                value_text = "기록 없음"
            else:
                value_text = f"{value}{f' {unit}' if unit else ''}"
            lines.append(f"- {label}: {value_text}")
    return "\n".join(lines)


def field_group_text(
    title: str,
    field_order: list[str],
    row: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
) -> str:
    lines = [f"**{title}**"]
    for field_name in field_order:
        field_meta = metadata[field_name]
        label = field_meta["label_ko"]
        unit = field_meta.get("unit", "")
        value = row.get(field_name)
        if value is None or pd.isna(value):
            value_text = "기록 없음"
        else:
            value_text = f"{value}{f' {unit}' if unit else ''}"
        lines.append(f"- {label}: {value_text}")
    return "\n".join(lines)


def escape_markdown_tildes(text: str) -> str:
    return text.replace("~", r"\~")


def post_trend_report_to_slack(
    summary_lines: list[str],
    full_analysis: str,
    today_row: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
    *,
    link: str | None = DEFAULT_APP_URL,
) -> str:
    summary_text = "\n".join(f"- {escape_markdown_tildes(line)}" for line in summary_lines[:3])
    main_text = f"*Ligi Biometrics 최근 트렌드 분석*\n{summary_text}"
    thread_messages = [
        today_values_text(today_row, metadata),
        f"*전체 분석*\n{escape_markdown_tildes(full_analysis)}",
    ]
    return slack_notify.post_threaded_message(
        main_text,
        thread_messages,
        link=link,
        fallback_to_webhook=True,
    )


def render_charts(df: pd.DataFrame) -> None:
    if df.empty:
        return

    chart_df = df.copy()
    chart_df[DATE_COLUMN] = pd.to_datetime(chart_df[DATE_COLUMN], errors="coerce")
    chart_df = chart_df.dropna(subset=[DATE_COLUMN]).set_index(DATE_COLUMN).sort_index()
    if chart_df.empty:
        return

    numeric_columns = [
        "weight_kg",
        "face_swelling",
        "hand_foot_swelling",
        "abdominal_bloating",
        "gas_distension",
        "fatigue_brain_fog",
        "sleep_quality",
    ]
    for column in numeric_columns:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")

    st.subheader("추세")
    if not chart_df[numeric_columns].notna().any().any():
        return

    plot_df = chart_df.reset_index()
    symptom_df = plot_df.melt(
        id_vars=[DATE_COLUMN],
        value_vars=[
            "face_swelling",
            "hand_foot_swelling",
            "abdominal_bloating",
            "gas_distension",
            "fatigue_brain_fog",
            "sleep_quality",
        ],
        var_name="metric",
        value_name="value",
    ).dropna(subset=["value"])
    symptom_df["metric"] = symptom_df["metric"].map(
        {
            "face_swelling": "얼굴 붓기",
            "hand_foot_swelling": "손발 붓기",
            "abdominal_bloating": "복부 팽만",
            "gas_distension": "장가스",
            "fatigue_brain_fog": "피로감/멍함",
            "sleep_quality": "수면 질",
        }
    )

    layers = []
    if not symptom_df.empty:
        layers.append(
            alt.Chart(symptom_df)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X(f"{DATE_COLUMN}:T", title="날짜"),
                y=alt.Y("value:Q", title="증상 점수", scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("metric:N", title="지표"),
                tooltip=[
                    alt.Tooltip(f"{DATE_COLUMN}:T", title="날짜"),
                    alt.Tooltip("metric:N", title="지표"),
                    alt.Tooltip("value:Q", title="값", format=".2f"),
                ],
            )
        )

    weight_df = plot_df[[DATE_COLUMN, "weight_kg"]].dropna(subset=["weight_kg"])
    if not weight_df.empty:
        layers.append(
            alt.Chart(weight_df)
            .mark_line(point=True, strokeDash=[5, 3], color="#111827", strokeWidth=2)
            .encode(
                x=alt.X(f"{DATE_COLUMN}:T", title="날짜"),
                y=alt.Y("weight_kg:Q", title="몸무게 (kg)", axis=alt.Axis(orient="right")),
                tooltip=[
                    alt.Tooltip(f"{DATE_COLUMN}:T", title="날짜"),
                    alt.Tooltip("weight_kg:Q", title="몸무게", format=".1f"),
                ],
            )
        )

    if layers:
        chart = alt.layer(*layers).resolve_scale(y="independent").properties(height=260)
        st.altair_chart(chart, use_container_width=True)


def render_step_heading(title: str) -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def render_cause_page(
    metadata: dict[str, dict[str, Any]],
    today_row: dict[str, Any] | None,
    previous_row: dict[str, Any] | None,
) -> None:
    render_step_heading("전날 원인 입력")
    with st.form("cause_form"):
        cause_values = render_form_fields(
            metadata,
            CAUSE_FIELD_ORDER,
            today_row,
            previous_row,
            "cause",
        )
        next_clicked = st.form_submit_button("다음으로", type="primary")

    if next_clicked:
        st.session_state[CAUSE_DRAFT_KEY] = normalize_submitted_values(cause_values, metadata)
        st.session_state[PAGE_KEY] = "results"
        st.rerun()


def render_result_input_page(
    metadata: dict[str, dict[str, Any]],
    today_row: dict[str, Any] | None,
    previous_row: dict[str, Any] | None,
    df: pd.DataFrame,
    today_iso: str,
) -> pd.DataFrame:
    render_step_heading("오늘 결과 입력")
    _spacer_col, back_col = st.columns([1, 0.48])
    with back_col:
        if st.button("전날 원인으로 돌아가기"):
            st.session_state[PAGE_KEY] = "causes"
            st.rerun()

    cause_values = st.session_state.get(CAUSE_DRAFT_KEY)
    if cause_values is None:
        cause_values = {
            field_name: stored_or_default_value(field_name, metadata[field_name], today_row)
            for field_name in CAUSE_FIELD_ORDER
        }
        st.session_state[CAUSE_DRAFT_KEY] = cause_values

    with st.form("result_form"):
        result_values = render_form_fields(
            metadata,
            RESULT_FIELD_ORDER,
            today_row,
            previous_row,
            "result",
        )
        submitted = st.form_submit_button("저장하고 분석하기", type="primary")

    if not submitted:
        return df

    normalized_results = normalize_submitted_values(result_values, metadata)
    row_values = {**cause_values, **normalized_results}
    updated_df = upsert_today(df, today_iso, row_values)
    sheets_saved = save_data(updated_df)
    if sheets_saved:
        st.success("오늘 기록을 Google Sheets에 저장했습니다.")
    else:
        st.warning("오늘 기록을 로컬 CSV에는 저장했지만 Google Sheets 저장은 실패했습니다.")
        with st.expander("Google Sheets 연결 진단", expanded=True):
            for name, ok, detail in diagnose_sheets_connection():
                status = "OK" if ok else "FAIL"
                st.write(f"{status} - {name}: {detail}")

    prompt_today, prompt_yesterday, prompt_recent = rows_for_prompt(updated_df, today_iso)
    with st.spinner("한국어 트렌드 분석을 생성하는 중입니다..."):
        try:
            trend_report = generate_trend_report(prompt_today, prompt_yesterday, prompt_recent)
        except Exception as exc:
            trend_report = {
                "summary_lines": ["분석 생성 중 오류가 발생했습니다.", "저장된 데이터는 유지되었습니다.", str(exc)],
                "full_analysis": f"분석 생성 중 오류가 발생했습니다: {exc}",
            }

    st.session_state["latest_trend_report"] = trend_report
    st.session_state["latest_saved_row"] = prompt_today
    st.session_state["latest_df"] = updated_df
    st.session_state[PAGE_KEY] = "analysis"
    try:
        slack_post_mode = post_trend_report_to_slack(
            trend_report["summary_lines"],
            trend_report["full_analysis"],
            prompt_today,
            metadata,
            link=DEFAULT_APP_URL,
        )
        st.session_state["latest_slack_post_mode"] = slack_post_mode
    except Exception as exc:
        st.session_state["latest_slack_error"] = str(exc)
    st.rerun()


def render_analysis_page(
    metadata: dict[str, dict[str, Any]],
    df: pd.DataFrame,
) -> None:
    render_step_heading("전체 저장 분석 결과 및 추세")
    report = st.session_state.get("latest_trend_report")
    saved_row = st.session_state.get("latest_saved_row")

    if report:
        st.subheader("최근 트렌드 분석")
        summary_lines = report.get("summary_lines", [])[:3]
        if summary_lines:
            st.markdown("\n".join(f"- {escape_markdown_tildes(line)}" for line in summary_lines))
        st.markdown(escape_markdown_tildes(report["full_analysis"]))

    if saved_row:
        st.markdown(field_group_text("전날 원인", CAUSE_FIELD_ORDER, saved_row, metadata))
        st.markdown(field_group_text("오늘 결과", RESULT_FIELD_ORDER, saved_row, metadata))

    slack_mode = st.session_state.pop("latest_slack_post_mode", None)
    slack_error = st.session_state.pop("latest_slack_error", None)
    if slack_mode == "thread":
        st.success("분석 요약과 상세 내용을 Slack thread로 전송했습니다.")
    elif slack_mode == "webhook":
        st.warning(
            "Slack thread 권한이 없어 입력값과 전체 분석을 단일 Slack 메시지로 전송했습니다. "
            "thread 전송에는 SLACK_BOT_TOKEN과 SLACK_CHANNEL_ID가 필요합니다."
        )
    elif slack_error:
        st.warning(f"Slack 전송에 실패했습니다: {slack_error}")

    st.subheader("추세 그래프")
    render_charts(df)

    with st.expander("최근 14일 데이터", expanded=False):
        st.dataframe(df.sort_values(DATE_COLUMN, ascending=False).head(14), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("오늘 기록 수정"):
            st.session_state[PAGE_KEY] = "causes"
            st.rerun()
    with col2:
        if st.button("결과 다시 보기"):
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Ligi Biometrics", page_icon="LB", layout="wide")
    apply_compact_styles()
    install_input_select_script()

    metadata = load_metadata()
    df = load_data()
    today_iso = current_date_iso()
    today_row = get_today_row(df, today_iso)
    yesterday_row = get_latest_previous_row(df, today_iso)

    render_header(today_iso)

    page = st.session_state.setdefault(PAGE_KEY, "causes")
    if page == "results":
        render_result_input_page(metadata, today_row, yesterday_row, df, today_iso)
    elif page == "analysis":
        render_analysis_page(metadata, st.session_state.get("latest_df", df))
    else:
        render_cause_page(metadata, today_row, yesterday_row)


if __name__ == "__main__":
    main()
