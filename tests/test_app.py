import unittest

from thread_plot.app import metric_messages


class AppTests(unittest.TestCase):
    def test_keeps_metric_rows_authored_by_other_bots(self):
        messages = [
            {"ts": "1.0", "text": "update=481 success_rate=0.44", "bot_id": "B_METRICS"},
            {"ts": "2.0", "text": "<@B_PLOT> success_rate --x update"},
        ]
        self.assertEqual(metric_messages(messages, "2.0"), [messages[0]])
