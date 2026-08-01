# SLIME CORE lunch

Ollama 経由で動く、音声読み上げつきの Slimecore です。通常会話に加えて、古文資料をPDFまたはOCR JSONから現代語訳へ変換できます。

「lunch」は手軽さ（お昼ごはんのように軽く使える）と起動（launch）の掛詞です。

## 入っているもの

- `app.py` : Streamlit の会話アプリ
- `assets/slimecore_flat.jpeg` : キャラクター画像
- `requirements.txt` : 必要な Python パッケージ
- `launch.command` : Finder から起動するためのファイル
- `data/chats/` : 会話ログ保存先
- `modules/` : 古文処理パイプライン
- `app_config.json` : OCR・PDF・フィルタ・Ollamaの設定
- `outputs/` : 古文処理セッションの保存先
- `tests/` : 信頼度判定と訳文組み立ての自動テスト
- `last_launch.log` : 直近の起動ログ
- `SPEC_JA.md` : 詳細仕様書

## 起動

Finder で `launch.command` をダブルクリックしてください。

ターミナルから起動する場合:

```bash
cd ~/Desktop/SLIMEcore_lun
./launch.command
```

ブラウザは自動で開きます。通常は次のアドレスです。

```text
http://localhost:8502
```

もし `Port 8502 is already in use` と出る場合は、起動ファイルが自動で `8503`, `8504`... のように空いている番号へ切り替えます。サーバーが応答できるようになってからブラウザを開きます。

うまく開かない場合は、同じフォルダーの `last_launch.log` に起動ログが残ります。

## Ollama

起動時に Ollama が止まっていれば `ollama serve` を試します。モデルはアプリ内のサイドバーから選べます。既定は `gemma4:26b` です。

すでに入っているモデルを使う場合は追加作業なしで動きます。新しく入れる場合:

```bash
ollama pull gemma4:26b
```

## 入力と表示

画面はサイドバー＋メインの2カラム構成です。サイドバー上部の `Language` で日本語 / English を切り替えられます。メイン領域は次の順番です。

1. コメント欄
2. コメントの真下に最新回答
3. その下に会話ログ

Enter 送信は日本語変換に合わせた二度押し方式です。

- Enter 1回目: 送信待機
- Enter 2回目: AIへ送信
- 日本語変換中の Enter: 送信しません
- Shift+Enter: 改行
- サイドバーで Enter 二度押し送信の ON/OFF と猶予秒を調整できます

Enter 1回目の待機中は、送信ボタンが「もう一度 Enter で送信」または「Press Enter again to send」に変わり、色のフェードで残り時間を示します。

## 表示の安定性

上部の大見出しは日本語フォントで見切れないよう、余白と行高を広めに取っています。

## 応答中

Ollama の応答待ち中は、最新回答エリアに「考えています...」を表示し、コメント欄と送信ボタンを一時的に無効化します。

## 会話ログ

画面表示は直近40メッセージまでです。古い会話がある場合は「（古い会話は省略されています）」と表示します。

JSONログには古い会話も残します。ログファイルはセッション開始時の日付で作成し、日をまたいでも同一セッション中は同じファイルへ保存します。

## 音声

macOS の `say` コマンドで返答を読み上げます。サイドバーで次を調整できます。

- 自動読み上げ ON/OFF
- 声の種類
- 読み上げ速度

ボタン `最後の返答をもう一度読む` で再読み上げできます。返答が900文字を超える場合、読み上げは先頭900文字までになり、最新回答エリアに注記を表示します。

## 古文処理

画面上部の「古文処理」タブからPDFまたはNDLOCR形式のJSONを選択できます。

- PDF: 全ページをPNGへ変換し、NDLOCR-Liteでページ単位のOCRを行います。
- OCR JSON: NDLOCR-Liteが未導入でも、信頼度判定と現代語訳の処理を確認できます。
- 低信頼度行または日本語文字比率が低い行は、推測で補わず `(原文不明瞭)` として訳文へ残します。
- 結果は `outputs/<session_id>/` に保存され、`translation.txt`、`manifest.json`、ページ画像、OCR JSON、フィルタ結果を含みます。

PDF処理にはNDLOCR-Liteと `pdftoppm` が必要です。標準構成では、アプリ内の `tools/ndlocr-lite-run` から専用のPython環境に導入したNDLOCR-Liteを起動します。`app_config.json` の `ocr.binary` と `ocr.args` を変更すると、別のOCRコマンドにも接続できます。

古文処理はバックグラウンドで実行されるため、処理中も会話タブを利用できます。

## 検証

~~~bash
cd ~/Desktop/SLIMEcore_lun
.venv/bin/python -m unittest discover -s tests -v
~~~

## 仕様書

詳細仕様は `SPEC_JA.md` にまとめています。
