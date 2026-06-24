"""Parsing for the @thread-plot command."""

from __future__ import annotations

from dataclasses import dataclass
import re
import shlex


class CommandError(ValueError):
    """A command could not be understood."""


FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
SLACK_URL_RE = re.compile(
    r"^https?://[^/]+/archives/(?P<channel>[A-Z0-9]+)/p(?P<seconds>\d{10})(?P<fraction>\d+)(?:[/?#].*)?$"
)


@dataclass(frozen=True)
class WhereCondition:
    key: str
    operator: str
    value: str | None = None

    def display(self) -> str:
        return f"{self.key}{self.operator}{self.value or ''}" if self.operator != "exists" else self.key


@dataclass(frozen=True)
class PlotCommand:
    y_fields: tuple[str, ...]
    x_field: str | None = None
    where: tuple[WhereCondition, ...] = ()
    last: int | None = None
    smooth: int | None = None
    title: str | None = None
    url: str | None = None

    @property
    def display_title(self) -> str:
        return self.title or f"{', '.join(self.y_fields)} vs {self.x_field or 'message order'}"


def _field(value: str, label: str) -> str:
    if not FIELD_RE.fullmatch(value):
        raise CommandError(f"{label} must be a field name, got {value!r}")
    return value


def parse_command(text: str) -> PlotCommand:
    """Parse command text after the Slack mention has been removed."""
    try:
        tokens = shlex.split(text)
    except ValueError as error:
        raise CommandError(f"invalid quoting: {error}") from error
    if not tokens:
        raise CommandError("at least one y field is required")

    y_fields: list[str] = []
    index = 0
    while index < len(tokens) and not tokens[index].startswith("--"):
        y_fields.append(_field(tokens[index], "y"))
        index += 1
    if not y_fields:
        raise CommandError("at least one y field is required")

    x_field: str | None = None
    where: list[WhereCondition] = []
    last: int | None = None
    smooth: int | None = None
    title: str | None = None
    url: str | None = None
    seen: set[str] = set()

    while index < len(tokens):
        option = tokens[index]
        index += 1
        if option not in {"--x", "--where", "--last", "--smooth", "--title", "--url"}:
            raise CommandError(f"unknown option: {option}")
        if index == len(tokens):
            raise CommandError(f"{option} needs a value")
        value = tokens[index]
        index += 1
        if option != "--where" and option in seen:
            raise CommandError(f"{option} may only be given once")
        seen.add(option)
        if option == "--x":
            x_field = _field(value, "x")
        elif option == "--where":
            where.append(parse_where(value))
        elif option in {"--last", "--smooth"}:
            try:
                number = int(value)
            except ValueError as error:
                raise CommandError(f"{option} must be a positive integer") from error
            if number < 1:
                raise CommandError(f"{option} must be a positive integer")
            if option == "--last":
                last = number
            else:
                smooth = number
        elif option == "--title":
            title = value
        else:
            parse_slack_thread_url(value)
            url = value

    return PlotCommand(tuple(y_fields), x_field, tuple(where), last, smooth, title, url)


def parse_where(value: str) -> WhereCondition:
    """Parse one presence, equality, or numeric-comparison filter."""
    if value.startswith("!") and len(value) > 1 and all(symbol not in value[1:] for symbol in "=<>!"):
        return WhereCondition(_field(value[1:], "where key"), "not_exists")
    if FIELD_RE.fullmatch(value):
        return WhereCondition(value, "exists")
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.-]*)(>=|<=|!=|=|>|<)(.+)", value)
    if not match:
        raise CommandError("--where must be KEY, !KEY, or KEY[!=<>]=VALUE")
    key, operator, expected = match.groups()
    return WhereCondition(_field(key, "where key"), operator, expected)


def parse_slack_thread_url(url: str) -> tuple[str, str]:
    """Return channel ID and Slack timestamp from a permalink to a root post."""
    match = SLACK_URL_RE.fullmatch(url)
    if not match:
        raise CommandError("--url must be a Slack /archives/<channel>/p<timestamp> URL")
    return match.group("channel"), f"{match.group('seconds')}.{match.group('fraction')}"


USAGE = (
    "Usage: @thread-plot <y...> [--x <x>] [--where <key=value>] "
    "[--last N] [--smooth N] [--title TEXT] [--url THREAD_ROOT_URL]"
)
