"""Pure response-destination rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Destination:
    channel: str
    thread_ts: str | None


def destinations(*, has_url: bool, target_channel: str, target_root_ts: str) -> tuple[Destination, ...]:
    """Normal invocations reply in-thread; URL invocations also post in-channel."""
    thread = Destination(target_channel, target_root_ts)
    return (thread, Destination(target_channel, None)) if has_url else (thread,)

