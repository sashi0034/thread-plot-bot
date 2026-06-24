# thread-plot

Slack スレッド内の `key=value` ログを、Pillow で PNG の折れ線グラフにする Socket Mode ボットです。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m thread_plot.app
```

`.env` に Slack App の Bot User OAuth Token（`xoxb-...`）と、`connections:write` を持つ App-Level Token（`xapp-...`）を設定してください。Socket Mode では Request URL は不要です。

Slack の **From an app manifest** で [slack-manifest.yml](slack-manifest.yml) を読み込み、アプリをワークスペースへインストールします。プライベートチャンネルの履歴を読むには、ボットをそのチャンネルへ招待してください。

## 使い方

スレッド内でボットをメンションします。ログ投稿は空白区切りの `key=value` です。

```text
reward=1.2 episode=10 curriculum=survival is_success=true
```

```text
@thread-plot reward --x episode --smooth 20
@thread-plot reward --x update --last 100 --smooth 10
@thread-plot policy_loss value_loss entropy --x update
@thread-plot reward --x episode --where curriculum=survival
@thread-plot reward --x episode --where is_success=true
```

`--x` を省略すると投稿順を横軸にします。`--where` は複数指定でき、文字列完全一致で絞り込みます。`--last` は絞り込み後の最新 N 投稿に適用し、`--smooth` は単純移動平均の窓幅です。`--title` に空白を含める場合は引用符で囲んでください。

別スレッドを対象にするには `--url` へスレッド親投稿の Slack URL を指定します。その場合は指定先スレッドと、そのチャンネル直下の両方に結果を投稿します。

```text
@thread-plot reward --x episode --url "https://workspace.slack.com/archives/C0123456789/p1712345678901234"
```

親投稿と他ボットのログ投稿も集計します。コマンド投稿だけは除外し、必須の y または x が数値でない投稿は除外され、結果要約に件数が表示されます。

## テスト

```bash
python -m unittest discover -s tests -v
```
