import unittest
from unittest.mock import Mock

from thread_plot.app import USAGE, _reply_error, metric_messages


class AppTests(unittest.TestCase):
    def test_keeps_metric_rows_authored_by_other_bots(self):
        messages = [
            {"ts": "1.0", "text": "update=481 success_rate=0.44", "bot_id": "B_METRICS"},
            {"ts": "2.0", "text": "<@B_PLOT> success_rate --x update"},
        ]
        self.assertEqual(metric_messages(messages, "2.0"), [messages[0]])

    def test_channel_level_error_is_not_posted_as_a_thread_reply(self):
        client = Mock()

        _reply_error(client, {"channel": "C1", "ts": "1.0"}, "bad command")

        self.assertEqual(
            client.chat_postMessage.call_args.kwargs,
            {"channel": "C1", "text": f"bad command\n{USAGE}"},
        )

    def test_thread_error_replies_in_the_existing_thread(self):
        client = Mock()

        _reply_error(client, {"channel": "C1", "ts": "2.0", "thread_ts": "1.0"}, "bad command")

        self.assertEqual(
            client.chat_postMessage.call_args.kwargs,
            {"channel": "C1", "thread_ts": "1.0", "text": f"bad command\n{USAGE}"},
        )
