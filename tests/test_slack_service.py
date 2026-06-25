import unittest
from unittest.mock import Mock, call, patch

from thread_plot.slack_service import FILE_LINK_BROADCAST_DELAY_SECONDS, SlackService


class SlackServiceTests(unittest.TestCase):
    def test_reads_paginated_thread_and_uploads_to_thread(self):
        client = Mock()
        client.conversations_replies.side_effect = [
            {"messages": [{"ts": "1.0"}], "response_metadata": {"next_cursor": "next"}},
            {"messages": [{"ts": "2.0"}], "response_metadata": {"next_cursor": ""}},
        ]
        client.files_upload_v2.return_value = {"file": {"permalink": "https://files.slack.com/files-pri/T1-F1/plot.png"}}
        service = SlackService(client)

        self.assertEqual(service.thread_messages("C1", "1.0"), [{"ts": "1.0"}, {"ts": "2.0"}])
        self.assertEqual(
            service.upload_plot("/tmp/plot.png", "C1", "summary", "1.0"),
            "https://files.slack.com/files-pri/T1-F1/plot.png",
        )

        self.assertEqual(client.conversations_replies.call_count, 2)
        self.assertEqual(client.files_upload_v2.call_args.kwargs["thread_ts"], "1.0")
        self.assertEqual(client.files_upload_v2.call_args.kwargs["initial_comment"], "summary")

    def test_share_file_link_is_a_broadcast_thread_reply(self):
        client = Mock()
        timeline = Mock()
        timeline.attach_mock(client.chat_postMessage, "post")
        with patch("thread_plot.slack_service.time.sleep") as sleep:
            timeline.attach_mock(sleep, "sleep")
            SlackService(client).share_file_link("C1", "1.0", "chart ready", "https://files.slack.com/plot.png")

        sleep.assert_called_once_with(FILE_LINK_BROADCAST_DELAY_SECONDS)
        self.assertEqual(
            timeline.mock_calls,
            [
                call.sleep(FILE_LINK_BROADCAST_DELAY_SECONDS),
                call.post(
                    channel="C1",
                    thread_ts="1.0",
                    reply_broadcast=True,
                    text="chart ready\nhttps://files.slack.com/plot.png",
                ),
            ],
        )
        self.assertEqual(
            client.chat_postMessage.call_args.kwargs,
            {
                "channel": "C1",
                "thread_ts": "1.0",
                "reply_broadcast": True,
                "text": "chart ready\nhttps://files.slack.com/plot.png",
            },
        )
