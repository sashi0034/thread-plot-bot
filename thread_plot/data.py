"""Convert Slack key=value messages into numeric plot data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .command import PlotCommand


@dataclass(frozen=True)
class PlotData:
    x: tuple[float, ...]
    series: dict[str, tuple[float, ...]]
    included: int
    excluded: int


def parse_fields(text: str) -> dict[str, str]:
    """Extract whitespace-delimited key=value fields; later duplicate keys win."""
    fields: dict[str, str] = {}
    for token in text.split():
        key, separator, value = token.partition("=")
        if separator and key and value:
            fields[key] = value
    return fields


def build_plot_data(messages: Iterable[Mapping[str, str]], command: PlotCommand) -> PlotData:
    """Filter records and return aligned numeric values in input (chronological) order."""
    filtered = [
        parse_fields(message.get("text", ""))
        for message in messages
    ]
    filtered = [
        fields for fields in filtered
        if all(fields.get(key) == expected for key, expected in command.where)
    ]
    if command.last is not None:
        filtered = filtered[-command.last:]

    x_values: list[float] = []
    series_values = {field: [] for field in command.y_fields}
    excluded = 0
    for fields in filtered:
        try:
            x_value = float(fields[command.x_field]) if command.x_field else float(len(x_values) + 1)
            values = {field: float(fields[field]) for field in command.y_fields}
        except (KeyError, TypeError, ValueError):
            excluded += 1
            continue
        x_values.append(x_value)
        for field, value in values.items():
            series_values[field].append(value)

    return PlotData(
        tuple(x_values),
        {field: tuple(values) for field, values in series_values.items()},
        len(x_values),
        excluded,
    )


def moving_average(values: tuple[float, ...], window: int | None) -> tuple[float, ...]:
    if window is None or window == 1:
        return values
    result: list[float] = []
    for index in range(len(values)):
        sample = values[max(0, index - window + 1):index + 1]
        result.append(sum(sample) / len(sample))
    return tuple(result)

