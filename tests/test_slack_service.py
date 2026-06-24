import unittest
from unittest.mock import Mock

from thread_plot.slack_service import SlackService


class SlackServiceTests(unittest.TestCase):
    def test_reads_paginated_thread_and_uploads_to_thread(self):
        client = Mock()
        client.conversations_replies.side_effect = [
            {"messages": [{"ts": "1.0"}], "response_metadata": {"next_cursor": "next"}},
            {"messages": [{"ts": "2.0"}], "response_metadata": {"next_cursor": ""}},
        ]
        service = SlackService(client)

        self.assertEqual(service.thread_messages("C1", "1.0"), [{"ts": "1.0"}, {"ts": "2.0"}])
        service.upload_plot("/tmp/plot.png", "C1", "summary", "1.0")

        self.assertEqual(client.conversations_replies.call_count, 2)
        self.assertEqual(client.files_upload_v2.call_args.kwargs["thread_ts"], "1.0")
        self.assertEqual(client.files_upload_v2.call_args.kwargs["initial_comment"], "summary")
