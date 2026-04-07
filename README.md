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

## Environment

- macOS
- Python 3.10+
- Streamlit
- Ollama

![HFLGIG-akAAx9Xd](https://github.com/user-attachments/assets/79684d32-2250-495b-8b67-82b8e7d4c09b)


---

## Setup

### 1. Ollama をインストール
ローカルLLMを動かすために Ollama を用意してください。

### 2. 必要なモデルを取得
例:

```bash



ollama pull gemma3:12b
bash launch.command
