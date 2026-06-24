import tempfile
import unittest
from pathlib import Path

from PIL import Image

from thread_plot.data import PlotData
from thread_plot.plot import render_plot
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
            (Destination("C1", "1.2"), Destination("C1", None)),
        )
