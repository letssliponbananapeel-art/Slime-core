# Slime Core

ローカルLLMを、もっと軽く、もっと親しみやすく使うための  
**シンプルなAIチャットアプリ**です。

**Slime Core** は、ローカル環境で動くLLMと会話しながら、  
小さなキャラクターアプリのような体験を目指した試作プロジェクトです。

会話、キャラクター表示、簡易ステータス表示、音声読み上げなどを組み合わせ、  
「ただのチャット画面」ではない、存在感のあるローカルAI体験を目指しています。

---

## Features

- ローカルLLMとのチャット
- シンプルで見やすいUI
- キャラクター画像表示
- 会話にあわせた雰囲気づくり
- 音声読み上げ対応
- 軽量な試作構成

---

## Concept

Slime Core は、  
高機能なAIシステムを作ることよりも、まず

**「ローカルで動くAIと気軽に向き合えること」**  
**「小さくても個性のある体験にすること」**

を重視しています。

大規模な製品ではなく、  
**世界観のあるローカルAI UIのプロトタイプ**として開発しています。

---

## Screenshots

**会話タブ**

![会話タブ](docs/screenshots/chat.png)

**古文処理タブ**

![古文処理タブ](docs/screenshots/kobun.png)

---

## Environment

- macOS
- Python 3.10+
- Streamlit
- Ollama

---

## Setup

### 1. Ollama をインストール

ローカルLLMを動かすために [Ollama](https://ollama.com/) を用意してください。

### 2. 必要なモデルを取得

例:

```bash
ollama pull gemma3:12b
```

### 3. 起動

`launch.command` を Finder からダブルクリックするか、ターミナルで実行します。

```bash
bash launch.command
```

初回は Python の仮想環境（`.venv`）の作成と依存関係のインストールが自動で走ります。起動後、ブラウザで `http://localhost:8502` が開きます。

---

## 古文処理（Classical Japanese）

「古文処理」タブから、古文資料のPDFまたは NDLOCR 形式の JSON を現代語訳へ変換できます。

- **PDF**: 全ページを画像化し、NDLOCR-Lite でページ単位のOCRを行います。
- **OCR JSON**: NDLOCR-Lite が未導入でも、信頼度判定と現代語訳の処理を確認できます。
- 信頼度が低い行は推測で補わず、`(原文不明瞭)` として訳文に残します。

PDFから処理する場合は NDLOCR-Lite と Poppler の導入が必要です。

```bash
# 1. Poppler（pdftoppm / pdfinfo）
brew install poppler

# 2. NDLOCR-Lite を専用の Python 環境へ
mkdir -p ~/tools && cd ~/tools
git clone https://github.com/ndl-lab/ndlocr-lite.git
cd ndlocr-lite
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 3. アプリから呼び出すラッパーを置く
mkdir -p <SLIMEcoreのフォルダー>/tools
cat > <SLIMEcoreのフォルダー>/tools/ndlocr-lite-run <<'EOF'
#!/bin/bash
set -euo pipefail
NDLOCR_DIR="$HOME/tools/ndlocr-lite"
cd "$NDLOCR_DIR/src"
exec "$NDLOCR_DIR/.venv/bin/python" ocr.py "$@"
EOF
chmod +x <SLIMEcoreのフォルダー>/tools/ndlocr-lite-run
```

`chmod +x` を忘れると、画面上は導入済みに見えたまま処理時に失敗します。詳しい手順・設定の変更方法・トラブル対応は [README_JA.md](README_JA.md#ndlocr-lite-の導入) にまとめています。

---

## Documentation

- [README_JA.md](README_JA.md) — 使い方の詳細
- [SPEC_JA.md](SPEC_JA.md) — 仕様書
