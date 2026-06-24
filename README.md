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

起動コンソールには、受信コマンド・対象スレッドの親投稿本文・取得件数・抽出件数が `INFO` で出力されます。各返信投稿の本文は `DEBUG` のみで出力するため、必要なときだけ `.env` に `LOG_LEVEL=DEBUG` を設定してください。

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

`--x` を省略すると投稿順を横軸にします。`--where` は複数指定でき、すべての条件に一致する投稿だけを残します。`key=value` / `key!=value` は文字列比較、`key>value` / `key>=value` / `key<value` / `key<=value` は数値比較、`key` はフィールドが存在する投稿、`!key` はフィールドがない投稿を指定します。`--last` は絞り込み後の最新 N 投稿に適用し、`--smooth` は単純移動平均の窓幅です。`--title` に空白を含める場合は引用符で囲んでください。

複数の y フィールドを指定した場合は、横軸を共有する縦並びのパネルとして描画します。各パネルは独立した y 軸を持つため、値のスケールが大きく異なる `success_rate` と `loss` なども読みやすくなります。

別スレッドを対象にするには `--url` へスレッド親投稿の Slack URL を指定します。その場合は指定先スレッドへグラフを投稿し、ファイルの Slack permalink を含むブロードキャスト返信も投稿します。

```text
@thread-plot reward --x episode --url "https://workspace.slack.com/archives/C0123456789/p1712345678901234"
```

各ユーザーの直近の成功したコマンド設定は、ボットの起動中だけ記憶されます。`@thread-plot --` でその設定を再実行できます。y フィールドを省略したコマンドでは、未指定の項目を前回設定から引き継ぎます。

```text
@thread-plot --
@thread-plot --url "https://workspace.slack.com/archives/C0123456789/p1712345678901234"
```

`--url` の後ろに空白区切りで複数のスレッド URL を渡せます。Slack が貼り付けリンクを展開した `<URL|表示URL>` 形式にも対応しています。各スレッドに同じ設定で個別にグラフを投稿します。

```text
@thread-plot reward --x episode --url https://workspace.slack.com/archives/C0123456789/p1712345678901234 https://workspace.slack.com/archives/C0123456789/p1712345678905678
```

親投稿と他ボットのログ投稿も集計します。コマンド投稿だけは除外し、必須の y または x が数値でない投稿は除外され、結果要約に件数が表示されます。

## テスト

```bash
python -m unittest discover -s tests -v
```
