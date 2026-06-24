import unittest

from thread_plot.command import parse_command
from thread_plot.data import build_plot_data, moving_average, parse_fields


class DataTests(unittest.TestCase):
    def test_fields_filter_invalid_rows_and_last(self):
        command = parse_command("reward loss --x episode --where is_success=true --last 3")
        messages = [
            {"text": "reward=1 loss=4 episode=1 is_success=true"},
            {"text": "reward=2 loss=3 episode=2 is_success=false"},
            {"text": "reward=3 loss=2 episode=3 is_success=true"},
            {"text": "reward=bad loss=1 episode=4 is_success=true"},
            {"text": "reward=5 loss=0 episode=5 is_success=true"},
        ]
        data = build_plot_data(messages, command)
        self.assertEqual(data.x, (3.0, 5.0))
        self.assertEqual(data.series["reward"], (3.0, 5.0))
        self.assertEqual(data.excluded, 1)

    def test_default_x_and_moving_average(self):
        data = build_plot_data([{"text": "reward=1"}, {"text": "reward=3"}], parse_command("reward"))
        self.assertEqual(data.x, (1.0, 2.0))
        self.assertEqual(moving_average((1.0, 3.0, 8.0), 2), (1.0, 2.0, 5.5))
        self.assertEqual(parse_fields("flag=true x=1"), {"flag": "true", "x": "1"})

