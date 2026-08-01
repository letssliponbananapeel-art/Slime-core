#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

LOG_FILE="$PWD/last_launch.log"
: > "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

pause_with_error() {
  local status="$?"
  echo ""
  echo "SLIME CORE の起動に失敗しました。"
  echo "ログ: $LOG_FILE"
  echo "この画面を閉じずに、表示されたエラーを確認してください。"
  read -r -p "Enter キーで閉じます..." _
  exit "$status"
}
trap pause_with_error ERR

BASE_PORT="${SLIMECORE_PORT:-8502}"

# 既存の Python 環境を再利用したい場合は、環境変数で渡す。
#   例: SLIMECORE_FALLBACK_PYTHON="$HOME/somewhere/.venv/bin/python" ./launch.command
LEGACY_PYTHON="${SLIMECORE_FALLBACK_PYTHON:-}"

is_port_free() {
  local port="$1"
  ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

PORT="$BASE_PORT"
while ! is_port_free "$PORT"; do
  echo "Port $PORT is already in use. Trying $((PORT + 1))..."
  PORT=$((PORT + 1))
  if [ "$PORT" -gt "$((BASE_PORT + 20))" ]; then
    echo "No free port found near $BASE_PORT."
    exit 1
  fi
done

if command -v ollama >/dev/null 2>&1; then
  if ! curl -s --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve >/tmp/slimecore_ollama.log 2>&1 &
    sleep 2
  fi
else
  echo "Ollama command was not found. Install Ollama first if chat cannot connect."
fi

# venv 作成に使う Python を選ぶ。
# macOS 標準の python3 は 3.9 (LibreSSL) のことがあり、urllib3 が
# NotOpenSSLWarning を出すため、新しいものがあればそちらを優先する。
pick_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if [ ! -x ".venv/bin/python" ]; then
  BOOTSTRAP_PYTHON="$(pick_python)" || {
    echo "python3 が見つかりません。Python 3 を導入してください。"
    exit 1
  }
  echo "Creating Python environment with $BOOTSTRAP_PYTHON..."
  "$BOOTSTRAP_PYTHON" -m venv .venv
fi

PYTHON=".venv/bin/python"
"$PYTHON" -m pip install --upgrade pip >/dev/null 2>&1 || true

if ! "$PYTHON" -c "import streamlit, requests, psutil, PIL" >/dev/null 2>&1; then
  echo "Installing Python packages..."
  if ! "$PYTHON" -m pip install -r requirements.txt; then
    if [ -n "$LEGACY_PYTHON" ] && [ -x "$LEGACY_PYTHON" ] \
      && "$LEGACY_PYTHON" -c "import streamlit, requests, psutil" >/dev/null 2>&1; then
      echo "Using SLIMECORE_FALLBACK_PYTHON as fallback."
      PYTHON="$LEGACY_PYTHON"
    else
      echo "Could not install required Python packages."
      exit 1
    fi
  fi
fi

URL="http://localhost:$PORT"
echo "Starting SLIME CORE server on $URL"
"$PYTHON" -m streamlit run app.py \
  --server.port "$PORT" \
  --server.address 127.0.0.1 \
  --server.headless true \
  --browser.gatherUsageStats false &
SERVER_PID="$!"

for attempt in $(seq 1 90); do
  if curl -s --max-time 1 "http://127.0.0.1:$PORT/_stcore/health" | grep -q "ok"; then
    echo "Opening SLIME CORE at $URL"
    open "$URL" >/dev/null 2>&1 || true
    echo "SLIME CORE is running. Close this terminal window to stop it."
    wait "$SERVER_PID"
    exit "$?"
  fi

  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "Streamlit stopped before it became ready."
    echo "---- launch log ----"
    tail -n 120 "$LOG_FILE" || true
    exit 1
  fi

  sleep 1
done

echo "Timed out waiting for Streamlit to become ready."
echo "Try opening this URL manually after a few seconds: $URL"
exit 1
