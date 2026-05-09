"""Slack incoming webhook posting helper.

Reads `SLACK_WEBHOOK_URL` from env (or `slack_webhook_url` from Streamlit secrets)
and posts plain-text or markdown-style messages.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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


def get_webhook_url() -> str | None:
    return _streamlit_secret("slack_webhook_url") or os.getenv("SLACK_WEBHOOK_URL")


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
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
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
            },
        ]

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
