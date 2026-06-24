"""In-memory per-user command settings."""

from __future__ import annotations

from threading import Lock

from .command import PlotCommand


class CommandHistory:
    """Store the most recent successfully completed command for each user.

    The application has no database, so settings intentionally last for the
    lifetime of the bot process.  A lock keeps Socket Mode's concurrent event
    handlers from corrupting the small shared cache.
    """

    def __init__(self) -> None:
        self._commands: dict[str, PlotCommand] = {}
        self._lock = Lock()

    def resolve(self, user_id: str, partial: PlotCommand) -> PlotCommand:
        with self._lock:
            previous = self._commands.get(user_id)
        return partial.inherit(previous)

    def save(self, user_id: str, command: PlotCommand) -> None:
        with self._lock:
            self._commands[user_id] = command
