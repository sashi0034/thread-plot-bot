"""Parsing for the @thread-plot command."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
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
    y_fields: tuple[str, ...] = ()
    x_field: str | None = None
    where: tuple[WhereCondition, ...] = ()
    last: int | None = None
    smooth: int | None = None
    title: str | None = None
    # ``url`` remains the first URL for compatibility with single-target
    # callers; new code should use ``urls``.
    url: str | None = None
    urls: tuple[str, ...] = ()
    specified: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.urls and self.url is None:
            object.__setattr__(self, "url", self.urls[0])
        elif self.url and not self.urls:
            object.__setattr__(self, "urls", (self.url,))
        elif self.url and self.urls and self.url != self.urls[0]:
            raise ValueError("url must be the first value in urls")

    @property
    def display_title(self) -> str:
        return self.title or f"{', '.join(self.y_fields)} vs {self.x_field or 'message order'}"

    def inherit(self, previous: "PlotCommand | None") -> "PlotCommand":
        """Fill values omitted from this command from the user's prior command."""
        if "y" in self.specified:
            return self
        if previous is None:
            raise CommandError("No previous settings found; specify at least one y field.")
        return PlotCommand(
            y_fields=self.y_fields if "y" in self.specified else previous.y_fields,
            x_field=self.x_field if "--x" in self.specified else previous.x_field,
            where=self.where if "--where" in self.specified else previous.where,
            last=self.last if "--last" in self.specified else previous.last,
            smooth=self.smooth if "--smooth" in self.specified else previous.smooth,
            title=self.title if "--title" in self.specified else previous.title,
            urls=self.urls if "--url" in self.specified else previous.urls,
            specified=self.specified,
        )


def _field(value: str, label: str) -> str:
    if not FIELD_RE.fullmatch(value):
        raise CommandError(f"{label} must be a field name, got {value!r}")
    return value


def parse_command(text: str) -> PlotCommand:
    """Parse command text after the Slack mention has been removed."""
    try:
        # Slack escapes comparison operators in event text (for example,
        # ``update>500`` arrives as ``update&gt;500``).
        tokens = shlex.split(unescape(text))
    except ValueError as error:
        raise CommandError(f"invalid quoting: {error}") from error
    if not tokens:
        raise CommandError("at least one y field is required")

    y_fields: list[str] = []
    index = 0
    while index < len(tokens) and not tokens[index].startswith("--"):
        y_fields.append(_field(tokens[index], "y"))
        index += 1

    # A bare ``--`` makes an otherwise empty repeat command unambiguous.
    if index < len(tokens) and tokens[index] == "--":
        index += 1
        if index < len(tokens):
            raise CommandError("-- may only be used by itself")

    x_field: str | None = None
    where: list[WhereCondition] = []
    last: int | None = None
    smooth: int | None = None
    title: str | None = None
    urls: list[str] = []
    seen: set[str] = set()

    while index < len(tokens):
        option = tokens[index]
        index += 1
        if option not in {"--x", "--where", "--last", "--smooth", "--title", "--url"}:
            raise CommandError(f"unknown option: {option}")
        if index == len(tokens):
            raise CommandError(f"{option} needs a value")
        if option != "--where" and option in seen:
            raise CommandError(f"{option} may only be given once")
        seen.add(option)
        if option == "--url":
            url_tokens: list[str] = []
            while index < len(tokens) and not tokens[index].startswith("--"):
                url_tokens.append(tokens[index])
                index += 1
            if not url_tokens:
                raise CommandError("--url needs a value")
            url_text = " ".join(url_tokens)
            # Slack turns pasted links into ``<URL|label>``.  In particular,
            # several pasted links are normally separated by spaces, not
            # commas, so extract complete mrkdwn links before splitting.
            mrkdwn_urls = re.findall(r"<[^>]+>", url_text)
            if mrkdwn_urls:
                remainder = re.sub(r"<[^>]+>", "", url_text).replace(",", "").strip()
                if remainder:
                    raise CommandError("--url must contain only Slack thread URLs")
                pieces = mrkdwn_urls
            elif "," in url_text:
                pieces = [piece.strip() for piece in url_text.split(",")]
            else:
                pieces = url_tokens
            if any(not piece for piece in pieces):
                raise CommandError("--url values must be Slack thread URLs")
            for url in pieces:
                parse_slack_thread_url(url)
                urls.append(url)
            continue

        value = tokens[index]
        index += 1
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
        else:  # pragma: no cover - every supported option is handled above.
            raise AssertionError(f"unhandled option: {option}")

    if not y_fields and not seen and len(tokens) != 1:
        raise CommandError("at least one y field is required")

    specified = frozenset({"y"} if y_fields else set()) | frozenset(seen)
    return PlotCommand(
        y_fields=tuple(y_fields),
        x_field=x_field,
        where=tuple(where),
        last=last,
        smooth=smooth,
        title=title,
        urls=tuple(urls),
        specified=specified,
    )


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
    # Slack encodes pasted links in event payloads as <URL|display text>.
    # Accept both that mrkdwn representation and an ordinary URL.
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1].split("|", 1)[0]
    match = SLACK_URL_RE.fullmatch(url)
    if not match:
        raise CommandError("--url must be a Slack /archives/<channel>/p<timestamp> URL")
    return match.group("channel"), f"{match.group('seconds')}.{match.group('fraction')}"


USAGE = (
    "Usage: @thread-plot [<y...>] [--x <x>] [--where <key=value>] "
    "[--last N] [--smooth N] [--title TEXT] [--url URL [URL ...]]"
)
