import unittest

from thread_plot.command import CommandError, WhereCondition, parse_command, parse_slack_thread_url
from thread_plot.history import CommandHistory


class CommandTests(unittest.TestCase):
    def test_parse_all_options_and_repeated_where(self):
        command = parse_command(
            'reward loss --x episode --where curriculum=survival --where is_success=true '
            '--last 100 --smooth 10 --title "Training metrics" '
            '--url https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339'
        )
        self.assertEqual(command.y_fields, ("reward", "loss"))
        self.assertEqual(command.x_field, "episode")
        self.assertEqual(
            command.where,
            (WhereCondition("curriculum", "=", "survival"), WhereCondition("is_success", "=", "true")),
        )
        self.assertEqual((command.last, command.smooth, command.title), (100, 10, "Training metrics"))
        self.assertEqual(parse_slack_thread_url(command.url), ("C0B6GPFJ1FU", "1782284445.513339"))

    def test_parse_slack_mrkdwn_url(self):
        url = "<https://kmc-jp.slack.com/archives/C0B6GPFJ1FU/p1782284445513339|thread link>"
        self.assertEqual(parse_slack_thread_url(url), ("C0B6GPFJ1FU", "1782284445.513339"))

    def test_parse_html_escaped_comparison_operator(self):
        command = parse_command("success_rate --x update --where update&gt;500")
        self.assertEqual(command.where, (WhereCondition("update", ">", "500"),))

    def test_invalid_options_are_rejected(self):
        with self.assertRaises(CommandError):
            parse_command("reward --bogus 1")
        with self.assertRaises(CommandError):
            parse_command("reward --last 0")
        with self.assertRaises(CommandError):
            parse_command("reward --where =broken")

    def test_parse_all_where_forms(self):
        command = parse_command("reward --where flag --where !debug --where score!=0 --where x>1 --where x>=2 --where x<3 --where x<=4")
        self.assertEqual(
            command.where,
            (
                WhereCondition("flag", "exists"),
                WhereCondition("debug", "not_exists"),
                WhereCondition("score", "!=", "0"),
                WhereCondition("x", ">", "1"),
                WhereCondition("x", ">=", "2"),
                WhereCondition("x", "<", "3"),
                WhereCondition("x", "<=", "4"),
            ),
        )

    def test_parse_multiple_comma_separated_urls(self):
        command = parse_command(
            "reward --url "
            "https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339, "
            "https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445514444"
        )

        self.assertEqual(
            command.urls,
            (
                "https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339",
                "https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445514444",
            ),
        )
        self.assertEqual(command.url, command.urls[0])

    def test_parse_space_separated_slack_mrkdwn_urls(self):
        command = parse_command(
            "success_rate --x update --url "
            "<https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339|https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339> "
            "<https://example.slack.com/archives/C0B6GPFJ1FU/p1782302052704059|https://example.slack.com/archives/C0B6GPFJ1FU/p1782302052704059> "
            "<https://example.slack.com/archives/C0B6GPFJ1FU/p1782302100486919|https://example.slack.com/archives/C0B6GPFJ1FU/p1782302100486919>"
        )

        self.assertEqual(len(command.urls), 3)
        self.assertEqual(
            [parse_slack_thread_url(url) for url in command.urls],
            [
                ("C0B6GPFJ1FU", "1782284445.513339"),
                ("C0B6GPFJ1FU", "1782302052.704059"),
                ("C0B6GPFJ1FU", "1782302100.486919"),
            ],
        )

    def test_omitted_y_inherits_the_user_previous_settings(self):
        history = CommandHistory()
        original = parse_command(
            "reward loss --x episode --where curriculum=survival --last 100 --smooth 10 "
            "--title 'Training metrics'"
        )
        history.save("U1", original)

        repeated = history.resolve("U1", parse_command("--"))
        changed_url = history.resolve(
            "U1",
            parse_command("--url https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339"),
        )

        self.assertEqual(repeated.y_fields, ("reward", "loss"))
        self.assertEqual(repeated.x_field, "episode")
        self.assertEqual(repeated.where, (WhereCondition("curriculum", "=", "survival"),))
        self.assertEqual((repeated.last, repeated.smooth, repeated.title), (100, 10, "Training metrics"))
        self.assertEqual(changed_url.y_fields, ("reward", "loss"))
        self.assertEqual(changed_url.x_field, "episode")
        self.assertEqual(changed_url.urls, ("https://example.slack.com/archives/C0B6GPFJ1FU/p1782284445513339",))

    def test_explicit_y_does_not_inherit_previous_options(self):
        history = CommandHistory()
        history.save(
            "U1",
            parse_command("reward --x episode --where curriculum=survival --last 100 --smooth 10 --title Training"),
        )

        command = history.resolve("U1", parse_command("success_rate --x update"))

        self.assertEqual(command.y_fields, ("success_rate",))
        self.assertEqual(command.x_field, "update")
        self.assertEqual(command.where, ())
        self.assertIsNone(command.last)
        self.assertIsNone(command.smooth)
        self.assertIsNone(command.title)

    def test_repeat_without_a_prior_command_is_rejected(self):
        with self.assertRaisesRegex(CommandError, "No previous settings"):
            CommandHistory().resolve("U1", parse_command("--"))
