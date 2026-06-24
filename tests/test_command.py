import unittest

from thread_plot.command import CommandError, WhereCondition, parse_command, parse_slack_thread_url


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
