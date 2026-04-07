# SLIME CORE for macOS

## 同梱物
- app.py
- requirements.txt
- launch.command
- assets/ キャラクター画像

## 事前準備
1. Python 3 を入れる
2. Ollama を入れる
3. ターミナルで `ollama pull gemma4:26b` を実行

## 起動方法
### 方法1: ターミナル
```bash
cd slime_core_mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8502
```

### 方法2: Finder
- `launch.command` をダブルクリック

## 音声
- macOS の `say` コマンドで返答を読み上げます。

## モデル
- 既定は gemma4:26b です。
- アプリ内で 31b / e4b / e2b に切り替えできます。

## 画像
- `assets/` フォルダから読み込みます。
