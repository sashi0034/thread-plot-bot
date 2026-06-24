"""Pillow chart renderer with no matplotlib dependency."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from .data import PlotData, moving_average

WIDTH, HEIGHT = 1100, 680
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 95, 35, 65, 95
PANEL_GAP, MIN_PANEL_HEIGHT = 26, 210
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
    series_count = len(data.series)
    required_height = MARGIN_TOP + MARGIN_BOTTOM + series_count * MIN_PANEL_HEIGHT + (series_count - 1) * PANEL_GAP
    image_height = max(HEIGHT, required_height)
    image = Image.new("RGB", (WIDTH, image_height), "white")
    draw = ImageDraw.Draw(image)
    title_font, body_font, small_font = _font(24), _font(15), _font(13)
    left, right = MARGIN_LEFT, WIDTH - MARGIN_RIGHT
    top, bottom = MARGIN_TOP, image_height - MARGIN_BOTTOM
    x_low, x_high = _range(list(data.x))
    visible_series = {name: moving_average(values, smooth) for name, values in data.series.items()}
    panel_height = (bottom - top - PANEL_GAP * (series_count - 1)) / series_count
    x_ticks = x_tick_values(data.x, x_low, x_high)

    draw.text((left, 22), title, fill="#111827", font=title_font)

    for series_index, (name, values) in enumerate(visible_series.items()):
        color = COLORS[series_index % len(COLORS)]
        panel_top = top + series_index * (panel_height + PANEL_GAP)
        panel_bottom = panel_top + panel_height
        y_low, y_high = _range(list(values))
        for tick in range(6):
            y = panel_top + panel_height * tick / 5
            value = y_high - (y_high - y_low) * tick / 5
            draw.line((left, y, right, y), fill="#e5e7eb", width=1)
            label = f"{value:.4g}"
            box = draw.textbbox((0, 0), label, font=small_font)
            draw.text((left - (box[2] - box[0]) - 10, y - 8), label, fill="#4b5563", font=small_font)
        for value in x_ticks:
            x = _point(value, x_low, x_high, left, right)
            draw.line((x, panel_top, x, panel_bottom), fill="#f3f4f6", width=1)
        draw.line((left, panel_top, left, panel_bottom), fill="#374151", width=2)
        draw.line((left, panel_bottom, right, panel_bottom), fill="#374151", width=2)
        draw.rectangle((left + 8, panel_top + 8, left + 19, panel_top + 19), fill=color)
        draw.text((left + 26, panel_top + 4), name, fill="#111827", font=body_font)
        points = [
            (_point(x, x_low, x_high, left, right), _point(y, y_low, y_high, panel_top, panel_bottom, True))
            for x, y in zip(data.x, values)
        ]
        if len(points) == 1:
            px, py = points[0]
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color)
        else:
            draw.line(points, fill=color, width=3, joint="curve")

        if series_index == series_count - 1:
            for value in x_ticks:
                x = _point(value, x_low, x_high, left, right)
                label = str(int(value)) if value.is_integer() else f"{value:.4g}"
                box = draw.textbbox((0, 0), label, font=small_font)
                draw.text((x - (box[2] - box[0]) / 2, panel_bottom + 12), label, fill="#4b5563", font=small_font)
            draw.text((left, image_height - 38), x_label, fill="#374151", font=body_font)
    image.save(path, "PNG")
