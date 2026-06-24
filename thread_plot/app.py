"""Socket Mode entry point."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .command import CommandError, USAGE, parse_command, parse_slack_thread_url
from .data import build_plot_data
from .plot import render_plot
from .routing import destinations
from .slack_service import SlackService

MENTION_RE = re.compile(r"<@[A-Z0-9]+>")


def _summary(included: int, excluded: int, where: tuple[tuple[str, str], ...]) -> str:
    parts = [f"Generated graph from {included} row(s)"]
    if where:
        parts.append("where " + ", ".join(f"{key}={value}" for key, value in where))
    if excluded:
        parts.append(f"excluded {excluded} invalid row(s)")
    return " · ".join(parts)


def _reply_error(client: Any, event: dict[str, Any], message: str) -> None:
    client.chat_postMessage(channel=event["channel"], thread_ts=event.get("thread_ts") or event["ts"], text=f"{message}\n{USAGE}")


def register_handlers(app: App) -> None:
    @app.event("app_mention")
    def handle_mention(event: dict[str, Any], client: Any, logger: Any) -> None:
        try:
            command = parse_command(MENTION_RE.sub("", event.get("text", "")).strip())
            if command.url:
                target_channel, target_root_ts = parse_slack_thread_url(command.url)
            else:
                if not event.get("thread_ts"):
                    raise CommandError("Run this command in a thread, or supply --url THREAD_ROOT_URL.")
                target_channel, target_root_ts = event["channel"], event["thread_ts"]

            service = SlackService(client)
            raw_messages = service.thread_messages(target_channel, target_root_ts)
            messages = [
                message for message in raw_messages
                if message.get("ts") not in {target_root_ts, event.get("ts")}
                and message.get("bot_id") is None
            ]
            data = build_plot_data(messages, command)
            if not data.included:
                raise CommandError("No valid matching rows were found.")

            with tempfile.NamedTemporaryFile(prefix="thread-plot-", suffix=".png", delete=False) as output:
                output_path = Path(output.name)
            try:
                render_plot(
                    data,
                    title=command.display_title,
                    x_label=command.x_field or "message order",
                    smooth=command.smooth,
                    path=output_path,
                )
                summary = _summary(data.included, data.excluded, command.where)
                for destination in destinations(
                    has_url=command.url is not None,
                    target_channel=target_channel,
                    target_root_ts=target_root_ts,
                ):
                    service.upload_plot(output_path, destination.channel, summary, destination.thread_ts)
            finally:
                output_path.unlink(missing_ok=True)
        except CommandError as error:
            _reply_error(client, event, str(error))
        except Exception:
            logger.exception("thread-plot failed")
            _reply_error(client, event, "Unable to create the graph. Check the bot logs and thread permissions.")


def main() -> None:
    load_dotenv()
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not bot_token or not app_token:
        raise RuntimeError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set")
    app = App(token=bot_token)
    register_handlers(app)
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()

