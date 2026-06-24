"""Small Slack Web API adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SlackService:
    def __init__(self, client: Any) -> None:
        self.client = client

    def thread_messages(self, channel: str, root_ts: str) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            response = self.client.conversations_replies(channel=channel, ts=root_ts, limit=200, cursor=cursor)
            messages.extend(response.get("messages", []))
            cursor = response.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                return messages

    def upload_plot(self, path: str | Path, destination_channel: str, summary: str, thread_ts: str | None) -> str | None:
        kwargs: dict[str, Any] = {
            "channel": destination_channel,
            "file": str(path),
            "filename": "thread-plot.png",
            "title": "thread-plot",
            "initial_comment": summary,
        }
        if thread_ts is not None:
            kwargs["thread_ts"] = thread_ts
        response = self.client.files_upload_v2(**kwargs)
        uploaded_file = response.get("file") or next(iter(response.get("files", [])), {})
        permalink = uploaded_file.get("permalink") if isinstance(uploaded_file, dict) else None
        return permalink if isinstance(permalink, str) else None

    def share_file_link(
        self, destination_channel: str, thread_ts: str, summary: str, permalink: str
    ) -> None:
        """Post a broadcast reply linking to an uploaded file."""
        self.client.chat_postMessage(
            channel=destination_channel,
            thread_ts=thread_ts,
            reply_broadcast=True,
            text=f"{summary}\n{permalink}",
        )
