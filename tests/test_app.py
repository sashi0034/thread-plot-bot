import unittest
from unittest.mock import Mock

from thread_plot.app import USAGE, _reply_error, metric_messages, register_handlers
from thread_plot.history import CommandHistory


class FakeBoltApp:
    def __init__(self):
        self.handlers = {}

    def event(self, name):
        def register(handler):
            self.handlers[name] = handler
            return handler

        return register


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

    def test_multiple_urls_each_create_a_plot_and_are_reused(self):
        app = FakeBoltApp()
        register_handlers(app, CommandHistory())
        handler = app.handlers["app_mention"]
        client = Mock()
        client.conversations_replies.side_effect = [
            {"messages": [{"ts": "1.0"}, {"ts": "1.1", "text": "episode=1 reward=2"}]},
            {"messages": [{"ts": "2.0"}, {"ts": "2.1", "text": "episode=1 reward=3"}]},
            {"messages": [{"ts": "1.0"}, {"ts": "1.1", "text": "episode=1 reward=2"}]},
            {"messages": [{"ts": "2.0"}, {"ts": "2.1", "text": "episode=1 reward=3"}]},
        ]
        client.files_upload_v2.return_value = {"file": {"permalink": "https://files.slack.com/plot.png"}}
        logger = Mock()
        first = {
            "channel": "C_COMMAND",
            "ts": "9.0",
            "user": "U1",
            "text": (
                "<@B1> reward --x episode --url "
                "https://example.slack.com/archives/C1/p1700000000000001, "
                "https://example.slack.com/archives/C2/p1700000000000002"
            ),
        }

        handler(first, client, logger)
        handler({**first, "ts": "9.1", "text": "<@B1> --"}, client, logger)

        self.assertEqual(client.conversations_replies.call_count, 4)
        self.assertEqual(client.files_upload_v2.call_count, 4)
        self.assertEqual(client.chat_postMessage.call_count, 4)
