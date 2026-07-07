import unittest

from thread_plot.command import parse_command
from thread_plot.data import build_plot_data, matches_where, moving_average, parse_fields


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

    def test_fields_inside_slack_code_fence(self):
        text = (
            "update_1:\n"
            "```curriculum=random_opponents_4 update=1 success_rate=0.5 reward=2.0\n"
            "update_elapsed=7.0s```"
        )
        self.assertEqual(
            parse_fields(text),
            {
                "curriculum": "random_opponents_4",
                "update": "1",
                "success_rate": "0.5",
                "reward": "2.0",
                "update_elapsed": "7.0s",
            },
        )
        data = build_plot_data([{"text": text}], parse_command("success_rate reward --x update --where curriculum=random_opponents_4"))
        self.assertEqual(data.x, (1.0,))
        self.assertEqual(data.series["success_rate"], (0.5,))
        self.assertEqual(data.series["reward"], (2.0,))

    def test_where_presence_text_and_numeric_comparisons(self):
        fields = parse_fields("flag=true score=2.5 mode=train")
        checks = {
            "flag": True,
            "!debug": True,
            "mode=train": True,
            "mode!=eval": True,
            "score>2": True,
            "score>=2.5": True,
            "score<3": True,
            "score<=2.5": True,
            "score>bad": False,
            "missing!=x": False,
        }
        for expression, expected in checks.items():
            with self.subTest(expression=expression):
                self.assertEqual(matches_where(fields, parse_command(f"reward --where {expression}").where[0]), expected)
