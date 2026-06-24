import tempfile
import unittest
from pathlib import Path

from PIL import Image

from thread_plot.data import PlotData
from thread_plot.plot import render_plot, x_tick_values
from thread_plot.routing import Destination, destinations


class PlotAndRoutingTests(unittest.TestCase):
    def test_plot_writes_png_for_flat_multiple_series(self):
        data = PlotData((1.0, 2.0), {"reward": (3.0, 3.0), "loss": (1.0, 2.0)}, 2, 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plot.png"
            render_plot(data, title="Metrics", x_label="episode", smooth=2, path=path)
            self.assertTrue(path.exists())
            with Image.open(path) as image:
                self.assertEqual(image.format, "PNG")

    def test_destinations(self):
        self.assertEqual(destinations(has_url=False, target_channel="C1", target_root_ts="1.2"), (Destination("C1", "1.2"),))
        self.assertEqual(
            destinations(has_url=True, target_channel="C1", target_root_ts="1.2"),
            (Destination("C1", "1.2"),),
        )

    def test_integer_x_ticks_are_observed_integer_values(self):
        values = (481.0, 487.0, 500.0, 515.0, 540.0, 600.0, 650.0)
        ticks = x_tick_values(values, 467.48, 663.52)
        self.assertEqual(ticks[0], 481.0)
        self.assertEqual(ticks[-1], 650.0)
        self.assertTrue(all(tick in values and tick.is_integer() for tick in ticks))
