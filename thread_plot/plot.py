"""Pillow chart renderer with no matplotlib dependency."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from .data import PlotData, moving_average

WIDTH, HEIGHT = 1100, 680
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 95, 35, 65, 95
COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _range(values: list[float]) -> tuple[float, float]:
    low, high = min(values), max(values)
    if low == high:
        padding = abs(low) * 0.05 or 1.0
        return low - padding, high + padding
    padding = (high - low) * 0.08
    return low - padding, high + padding


def _point(value: float, low: float, high: float, start: float, end: float, invert: bool = False) -> float:
    ratio = (value - low) / (high - low)
    if invert:
        ratio = 1 - ratio
    return start + (end - start) * ratio


def x_tick_values(values: tuple[float, ...], low: float, high: float, maximum: int = 6) -> tuple[float, ...]:
    """Return readable x-axis ticks, preserving observed values for integer axes."""
    if all(value.is_integer() for value in values):
        observed = tuple(sorted(set(values)))
        if len(observed) <= maximum:
            return observed
        # Select evenly distributed observed values. This always keeps the
        # first/last data values and never fabricates an integer tick.
        last = len(observed) - 1
        return tuple(observed[index * last // (maximum - 1)] for index in range(maximum))
    return tuple(low + (high - low) * tick / (maximum - 1) for tick in range(maximum))


def render_plot(data: PlotData, *, title: str, x_label: str, smooth: int | None, path: str | Path) -> None:
    if not data.included:
        raise ValueError("no valid rows to plot")
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    title_font, body_font, small_font = _font(24), _font(15), _font(13)
    left, right = MARGIN_LEFT, WIDTH - MARGIN_RIGHT
    top, bottom = MARGIN_TOP, HEIGHT - MARGIN_BOTTOM
    x_low, x_high = _range(list(data.x))
    visible_series = {name: moving_average(values, smooth) for name, values in data.series.items()}
    y_low, y_high = _range([value for values in visible_series.values() for value in values])

    draw.text((left, 22), title, fill="#111827", font=title_font)
    for tick in range(6):
        y = top + (bottom - top) * tick / 5
        value = y_high - (y_high - y_low) * tick / 5
        draw.line((left, y, right, y), fill="#e5e7eb", width=1)
        label = f"{value:.4g}"
        box = draw.textbbox((0, 0), label, font=small_font)
        draw.text((left - (box[2] - box[0]) - 10, y - 8), label, fill="#4b5563", font=small_font)
    for value in x_tick_values(data.x, x_low, x_high):
        x = _point(value, x_low, x_high, left, right)
        draw.line((x, top, x, bottom), fill="#f3f4f6", width=1)
        label = str(int(value)) if value.is_integer() else f"{value:.4g}"
        box = draw.textbbox((0, 0), label, font=small_font)
        draw.text((x - (box[2] - box[0]) / 2, bottom + 12), label, fill="#4b5563", font=small_font)
    draw.line((left, top, left, bottom), fill="#374151", width=2)
    draw.line((left, bottom, right, bottom), fill="#374151", width=2)
    draw.text((left, HEIGHT - 38), x_label, fill="#374151", font=body_font)

    legend_x = right
    for series_index, (name, values) in enumerate(visible_series.items()):
        color = COLORS[series_index % len(COLORS)]
        points = [
            (_point(x, x_low, x_high, left, right), _point(y, y_low, y_high, top, bottom, True))
            for x, y in zip(data.x, values)
        ]
        if len(points) == 1:
            px, py = points[0]
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color)
        else:
            draw.line(points, fill=color, width=3, joint="curve")
        label_box = draw.textbbox((0, 0), name, font=small_font)
        label_width = label_box[2] - label_box[0]
        legend_x -= label_width + 31
        draw.line((legend_x, 52, legend_x + 18, 52), fill=color, width=3)
        draw.text((legend_x + 23, 44), name, fill="#111827", font=small_font)
        legend_x -= 14
    image.save(path, "PNG")
