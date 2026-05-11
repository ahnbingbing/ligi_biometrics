"""Slack incoming webhook posting helper.

Reads `SLACK_WEBHOOK_URL` from env or Streamlit secrets
and posts plain-text or markdown-style messages.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
MAX_SECTION_TEXT_LENGTH = 3000
SECTION_CHUNK_LENGTH = 2800


def _streamlit_secret(key: str) -> str | None:
    try:
        import streamlit as st  # type: ignore
        try:
            value = st.secrets[key]
            return str(value) if value else None
        except Exception:
            return None
    except ImportError:
        return None


def _first_streamlit_secret(*keys: str) -> str | None:
    for key in keys:
        value = _streamlit_secret(key)
        if value:
            return value
    return None


def get_webhook_url() -> str | None:
    load_dotenv(BASE_DIR / ".env")
    return (
        _first_streamlit_secret("SLACK_WEBHOOK_URL", "slack_webhook_url")
        or os.getenv("SLACK_WEBHOOK_URL")
    )


def get_app_url() -> str | None:
    load_dotenv(BASE_DIR / ".env")
    return _first_streamlit_secret("APP_URL", "app_url") or os.getenv("APP_URL")


def get_bot_token() -> str | None:
    load_dotenv(BASE_DIR / ".env")
    return _first_streamlit_secret("SLACK_BOT_TOKEN", "slack_bot_token") or os.getenv("SLACK_BOT_TOKEN")


def get_channel_id() -> str | None:
    load_dotenv(BASE_DIR / ".env")
    return _first_streamlit_secret("SLACK_CHANNEL_ID", "slack_channel_id") or os.getenv("SLACK_CHANNEL_ID")


def _split_section_text(text: str) -> list[str]:
    chunks: list[str] = []
    remaining = text
    while len(remaining) > MAX_SECTION_TEXT_LENGTH:
        split_at = remaining.rfind("\n", 0, SECTION_CHUNK_LENGTH)
        if split_at <= 0:
            split_at = SECTION_CHUNK_LENGTH
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _post_slack_api(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured.")

    data = json.dumps(payload).encode("utf-8")
    request = Request(
        f"https://slack.com/api/{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            result = json.loads(body)
            if response.status >= 300 or not result.get("ok"):
                raise RuntimeError(f"Slack API error: {body}")
            return result
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Slack API HTTP error {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Slack API connection error: {exc}") from exc


def _post_slack_thread_chunk(channel: str, thread_ts: str, chunk: str) -> None:
    payload = {
        "channel": channel,
        "thread_ts": thread_ts,
        "text": chunk,
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": chunk}}],
    }
    try:
        _post_slack_api("chat.postMessage", payload)
    except RuntimeError:
        _post_slack_api(
            "chat.postMessage",
            {
                "channel": channel,
                "thread_ts": thread_ts,
                "text": chunk,
            },
        )


def post_threaded_message(
    main_text: str,
    thread_text: str | list[str],
    *,
    link: str | None = None,
    fallback_to_webhook: bool = False,
) -> str:
    """Post a Slack main message and put details in its thread.

    Returns "thread" when posted through Slack Web API. If requested, missing
    bot credentials or Web API errors fall back to one incoming-webhook message
    and return "webhook".
    """
    channel = get_channel_id()
    token = get_bot_token()
    thread_messages = [thread_text] if isinstance(thread_text, str) else thread_text
    combined_text = "\n\n".join([main_text, *thread_messages])
    if not channel or not token:
        if not fallback_to_webhook:
            raise RuntimeError("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID are required for threaded messages.")
        post_message(combined_text, link=link)
        return "webhook"

    main_payload: dict[str, Any] = {"channel": channel, "text": main_text}
    if link:
        main_payload["blocks"] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": main_text}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "기록 보러가기"},
                        "url": link,
                        "style": "primary",
                    }
                ],
            },
        ]

    try:
        main_result = _post_slack_api("chat.postMessage", main_payload)
        thread_ts = main_result["ts"]
        for message in thread_messages:
            for chunk in _split_section_text(message):
                _post_slack_thread_chunk(channel, thread_ts, chunk)
        return "thread"
    except Exception:
        if not fallback_to_webhook:
            raise
        post_message(combined_text, link=link)
        return "webhook"


def post_message(text: str, *, link: str | None = None) -> None:
    """Post a message to the configured Slack webhook.

    Args:
        text: The message body. Slack mrkdwn is supported.
        link: Optional URL to surface as a button-style action below the text.

    Raises:
        RuntimeError: if no webhook URL is configured or the POST fails.
    """
    webhook = get_webhook_url()
    if not webhook:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL is not configured. Set env var or st.secrets['slack_webhook_url']."
        )

    payload: dict[str, Any] = {"text": text}
    if link:
        payload["blocks"] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": chunk}}
            for chunk in _split_section_text(text)
        ]
        payload["blocks"].append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "기록하러 가기"},
                        "url": link,
                        "style": "primary",
                    }
                ],
            }
        )

    data = json.dumps(payload).encode("utf-8")
    request = Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status >= 300:
                raise RuntimeError(f"Slack webhook error {response.status}: {body}")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Slack webhook HTTP error {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Slack webhook connection error: {exc}") from exc
