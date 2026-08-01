import datetime as dt
import html
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

import psutil
import requests
import streamlit as st
import streamlit.components.v1 as components

from modules.kobun_ui import render_kobun_panel


APP_DIR = Path(__file__).resolve().parent
ASSET_PATH = APP_DIR / "assets" / "slimecore_flat.jpeg"
CHAT_DIR = APP_DIR / "data" / "chats"

OLLAMA_HOST = "http://127.0.0.1:11434"
TAGS_API = f"{OLLAMA_HOST}/api/tags"
CHAT_API = f"{OLLAMA_HOST}/api/chat"

DEFAULT_MODEL = "gemma4:26b"
MODEL_PRIORITY = ["gemma4:26b", "gemma4:31b", "gemma3:27b", "gemma4:e4b", "gemma3:12b", "gemma3:latest"]
REQUEST_TIMEOUT = 300
UI_MESSAGE_LIMIT = 40
VOICE_CHAR_LIMIT = 900

SYSTEM_PROMPTS = {
    "ja": """
あなたは SLIME CORE。ローカル環境で動く会話AIです。
相手の意図を短く確認しながら、自然な日本語で、落ち着いた友人のように答えてください。
長すぎる説明は避け、必要なときだけ箇条書きを使ってください。
内部思考や推論過程は出さず、最終回答だけを返してください。
""".strip(),
    "en": """
You are SLIME CORE, a local conversational AI running through Ollama.
Reply in natural, concise English with a calm, friendly tone.
Avoid long explanations unless the user asks for detail. Use bullets only when they help.
Do not expose hidden reasoning or chain-of-thought. Return only the final answer.
""".strip(),
}

UI_TEXT = {
    "ja": {
        "language": "Language",
        "sidebar_copy": "Ollama で動く、声つきローカル会話AI。",
        "main_title": "会話",
        "main_subtitle": "コメント、最新回答、会話ログを一画面で扱います。",
        "comment": "コメント",
        "send": "送信",
        "send_again": "もう一度 Enter で送信",
        "read_last": "最後の返答をもう一度読む",
        "save_log": "会話ログを保存",
        "saved": "保存しました",
        "composer_help": "Enter は1回目で送信待機、2回目で送信します。日本語変換中の Enter は送信しません。改行は Shift+Enter。",
        "placeholder": "SLIME CORE に話しかける",
        "latest_answer": "最新回答",
        "answer_placeholder": "SLIME CORE の返答はここに表示されます。",
        "thinking": "考えています...",
        "chat_log": "会話ログ",
        "empty_log": "会話を始めると、この下へログが続きます。",
        "omitted": "（古い会話は省略されています）",
        "voice_limit": "（読み上げは先頭 900 文字までです）",
        "enter_toggle": "Enter 二度押し送信",
        "enter_grace": "Enter 猶予秒",
        "auto_voice": "返答を自動で読み上げ",
        "clear_chat": "会話をクリア",
        "ollama_online": "Ollama online",
        "ollama_missing": "Ollama が見つかりません。https://ollama.com からインストールしてください。",
        "ollama_connecting": "Ollama に接続できません。起動を試みています...",
        "ollama_connection_error": "Ollama に接続できません。`ollama serve` が起動しているか確認してください。",
        "timeout_error": "応答がタイムアウトしました。短い質問にするか、軽いモデルへ切り替えてください。",
        "empty_response": "返答を受け取れませんでした。もう一度だけ短く話しかけてください。",
        "voice_failed": "音声の起動に失敗",
        "voice_ready": "macOS voice ready",
        "voice_unavailable": "voice unavailable",
        "active_model": "ACTIVE MODEL",
        "voice": "VOICE",
        "model_label": "Ollama model",
        "max_response": "max response",
        "speech_rate": "speech rate",
        "system_default": "System Default",
        "chat_tab": "会話",
        "kobun_tab": "古文処理",
    },
    "en": {
        "language": "Language",
        "sidebar_copy": "A local voice-enabled chat AI powered by Ollama.",
        "main_title": "Chat",
        "main_subtitle": "Write a comment, read the latest answer, and keep the log below.",
        "comment": "Comment",
        "send": "Send",
        "send_again": "Press Enter again to send",
        "read_last": "Read Last Answer Again",
        "save_log": "Save Chat Log",
        "saved": "Saved",
        "composer_help": "Press Enter once to arm sending, then Enter again to send. IME composition Enter will not send. Shift+Enter inserts a line break.",
        "placeholder": "Talk to SLIME CORE",
        "latest_answer": "Latest Answer",
        "answer_placeholder": "SLIME CORE's answer will appear here.",
        "thinking": "Thinking...",
        "chat_log": "Chat Log",
        "empty_log": "Start a conversation and the log will continue below.",
        "omitted": "(Older messages are hidden.)",
        "voice_limit": "(Speech playback is limited to the first 900 characters.)",
        "enter_toggle": "Double-Enter Send",
        "enter_grace": "Enter Grace Seconds",
        "auto_voice": "Read answers aloud",
        "clear_chat": "Clear Chat",
        "ollama_online": "Ollama online",
        "ollama_missing": "Ollama was not found. Install it from https://ollama.com.",
        "ollama_connecting": "Cannot connect to Ollama. Trying to start it...",
        "ollama_connection_error": "Cannot connect to Ollama. Check that `ollama serve` is running.",
        "timeout_error": "The response timed out. Try a shorter prompt or switch to a lighter model.",
        "empty_response": "No response came back. Please try again with a shorter message.",
        "voice_failed": "Voice playback failed",
        "voice_ready": "macOS voice ready",
        "voice_unavailable": "voice unavailable",
        "active_model": "ACTIVE MODEL",
        "voice": "VOICE",
        "model_label": "Ollama model",
        "max_response": "max response",
        "speech_rate": "speech rate",
        "system_default": "System Default",
        "chat_tab": "Chat",
        "kobun_tab": "Classical Text",
    },
}


st.set_page_config(
    page_title="SLIME CORE",
    page_icon="SC",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
    --bg: #08090c;
    --panel: #10151a;
    --panel-2: #15181f;
    --line: rgba(155, 214, 201, 0.22);
    --mint: #7cf5d0;
    --cyan: #6fc9ff;
    --amber: #ffbd66;
    --rose: #ff6d8a;
    --text: #e8f2ef;
    --muted: #9fb1ad;
}
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stMain {
    background: var(--bg) !important;
    color: var(--text) !important;
}
[data-testid="stHeader"] {
    background: var(--bg) !important;
}
[data-testid="stMain"] .block-container {
    background: var(--bg) !important;
}
.stTextInput input, .stTextArea textarea, [data-baseweb="input"] > div,
[data-baseweb="select"] > div, [data-baseweb="base-input"] {
    background: var(--panel-2) !important;
    color: var(--text) !important;
    border-color: rgba(155, 214, 201, 0.24) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: var(--muted) !important;
}
[data-testid="stFileUploader"] {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px;
}
[data-testid="stFileUploader"] section {
    background: var(--panel-2) !important;
    color: var(--text) !important;
}
[data-testid="stFileUploader"] section * {
    color: var(--muted) !important;
}
[data-testid="stFileUploader"] button {
    background: rgba(124,245,208,0.08) !important;
    color: var(--text) !important;
    border-color: rgba(124,245,208,0.34) !important;
}
[data-testid="stFileUploader"] button * {
    color: var(--text) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    border-bottom-color: rgba(255,255,255,0.13) !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
    color: var(--muted) !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--rose) !important;
}
[data-testid="stExpander"] details {
    background: var(--panel) !important;
    border-color: var(--line) !important;
    border-radius: 8px;
}
[data-testid="stExpander"] summary, [data-testid="stFileUploader"] label,
.stTextInput label, .stTextArea label, .stMarkdown, .stCaption {
    color: var(--text) !important;
}
.block-container {
    max-width: 1120px;
    padding-top: 4.2rem;
    padding-bottom: 1.6rem;
}
[data-testid="stSidebar"] {
    background: #0b0e12 !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}
[data-testid="stSidebar"] .block-container {
    padding-top: 2rem;
}
h1, h2, h3 {
    letter-spacing: 0;
}
.sidebar-title {
    color: var(--text);
    font-size: 1.6rem;
    line-height: 1.28;
    font-weight: 800;
    margin: 0 0 0.35rem;
    padding-top: 0.2rem;
}
.sidebar-copy {
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.65;
    margin-bottom: 0.75rem;
}
.main-title {
    color: var(--text);
    font-size: clamp(1.8rem, 3.8vw, 3.05rem);
    line-height: 1.36;
    font-weight: 800;
    margin: 0 0 0.2rem;
    padding-top: 0.35rem;
    overflow: visible;
}
.main-subtitle {
    color: var(--muted);
    font-size: 0.94rem;
    line-height: 1.55;
    margin: 0 0 1rem;
}
.status-row {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
    margin: 0.8rem 0;
}
.pill {
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 999px;
    padding: 0.28rem 0.52rem;
    font-size: 0.74rem;
    color: var(--muted);
    overflow-wrap: anywhere;
}
.pill-ok { color: var(--mint); border-color: rgba(124,245,208,0.35); }
.pill-warn { color: var(--amber); border-color: rgba(255,189,102,0.38); }
.pill-bad { color: var(--rose); border-color: rgba(255,109,138,0.38); }
.metric-card {
    background: linear-gradient(180deg, rgba(20,24,31,0.98), rgba(12,14,18,0.98));
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.8rem;
    margin-top: 0.7rem;
}
.metric-label {
    color: var(--muted);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0;
}
.metric-value {
    color: var(--text);
    font-size: 1rem;
    font-weight: 700;
    overflow-wrap: anywhere;
}
.small-note {
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.65;
}
.warn-note {
    color: var(--amber);
    font-size: 0.82rem;
    line-height: 1.55;
}
.composer-heading {
    color: var(--text);
    font-size: 0.95rem;
    font-weight: 700;
    margin-top: 0.1rem;
}
.composer-help {
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.45;
    margin: 0.2rem 0 0.55rem;
}
.chat-log-title {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0;
    margin: 1rem 0 0.5rem;
}
textarea[aria-label="slime_textarea"] {
    min-height: 102px !important;
    line-height: 1.55 !important;
}
.latest-answer-panel {
    background: linear-gradient(180deg, rgba(18,25,31,0.98), rgba(11,14,18,0.98));
    border: 1px solid rgba(111,201,255,0.3);
    border-left: 4px solid var(--cyan);
    border-radius: 8px;
    padding: 0.9rem 1rem;
    margin: 0.75rem 0 1rem;
}
.latest-answer-waiting {
    border-left-color: var(--amber);
}
.latest-answer-label {
    color: var(--cyan);
    font-size: 0.78rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}
.latest-answer-waiting .latest-answer-label {
    color: var(--amber);
}
.latest-answer-text {
    color: var(--text);
    font-size: 0.98rem;
    line-height: 1.75;
}
.stButton > button {
    border-radius: 6px !important;
    border: 1px solid rgba(124,245,208,0.34) !important;
    background: rgba(124,245,208,0.08) !important;
    color: var(--text) !important;
}
.stButton > button:hover {
    border-color: rgba(111,201,255,0.75) !important;
    background: rgba(111,201,255,0.12) !important;
}
img {
    border-radius: 8px;
}
</style>
""",
    unsafe_allow_html=True,
)


def now_label() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_key() -> str:
    return dt.datetime.now().strftime("%Y%m%d")


def get_ui_text(language_code: str) -> dict[str, str]:
    return UI_TEXT.get(language_code, UI_TEXT["ja"])


def system_prompt_for(language_code: str) -> str:
    return SYSTEM_PROMPTS.get(language_code, SYSTEM_PROMPTS["ja"])


def init_state() -> None:
    defaults = {
        "messages": [],
        "last_spoken_index": -1,
        "auto_voice": True,
        "voice_name": "Kyoko",
        "speech_rate": 180,
        "temperature": 0.35,
        "num_predict": 360,
        "selected_model": DEFAULT_MODEL,
        "last_error": "",
        "input_nonce": 0,
        "enter_submit_enabled": True,
        "enter_grace_secs": 1.8,
        "processing_prompt": "",
        "voice_limit_note": False,
        "session_started_at": now_label(),
        "session_log_date": today_key(),
        "ui_language": "ja",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_installed_models(ui: dict[str, str]) -> tuple[bool, list[str], str]:
    try:
        response = requests.get(TAGS_API, timeout=6)
        response.raise_for_status()
        payload = response.json()
        models = [item.get("name", "") for item in payload.get("models", [])]
        return True, [model for model in models if model], ui["ollama_online"]
    except Exception as exc:
        if shutil.which("ollama") is None:
            message = ui["ollama_missing"]
        else:
            message = ui["ollama_connecting"]
        st.session_state.last_error = str(exc)
        return False, [], message


def ordered_models(models: list[str]) -> list[str]:
    preferred = [model for model in MODEL_PRIORITY if model in models]
    rest = [model for model in models if model not in preferred]
    return preferred + sorted(rest)


def choose_model(models: list[str]) -> str:
    if st.session_state.selected_model in models:
        return st.session_state.selected_model
    for model in MODEL_PRIORITY:
        if model in models:
            st.session_state.selected_model = model
            return model
    if models:
        st.session_state.selected_model = models[0]
        return models[0]
    return st.session_state.selected_model


@st.cache_data(ttl=600)
def get_macos_voice_options() -> list[str]:
    if platform.system() != "Darwin":
        return ["System Default"]
    try:
        result = subprocess.run(
            ["say", "-v", "?"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ["System Default"]

    parsed: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        match = re.match(r"^(.+?)\s+([a-z]{2}_[A-Z]{2})\s+#", line)
        if match:
            parsed.append((match.group(1).strip(), match.group(2)))

    japanese = [name for name, locale in parsed if locale == "ja_JP"]
    english = [name for name, locale in parsed if locale.startswith("en_")][:8]
    options = ["System Default"] + japanese + english
    seen = set()
    return [voice for voice in options if not (voice in seen or seen.add(voice))]


def visible_messages() -> list[dict[str, str]]:
    return st.session_state.messages[-UI_MESSAGE_LIMIT:]


def has_omitted_messages() -> bool:
    return len(st.session_state.messages) > UI_MESSAGE_LIMIT


def build_ollama_messages(user_text: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt_for(st.session_state.ui_language)}]
    for item in st.session_state.messages[-UI_MESSAGE_LIMIT:]:
        role = "assistant" if item["role"] == "assistant" else "user"
        messages.append({"role": role, "content": item["content"]})
    messages.append({"role": "user", "content": user_text})
    return messages


def call_ollama(user_text: str, model: str, ui: dict[str, str]) -> str:
    payload = {
        "model": model,
        "messages": build_ollama_messages(user_text),
        "stream": False,
        "think": False,
        "options": {
            "temperature": float(st.session_state.temperature),
            "num_predict": int(st.session_state.num_predict),
        },
    }
    try:
        response = requests.post(CHAT_API, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        content = ((data.get("message") or {}).get("content") or "").strip()
        if content:
            st.session_state.last_error = ""
            return content
        return ui["empty_response"]
    except requests.exceptions.ConnectionError:
        return ui["ollama_connection_error"]
    except requests.exceptions.Timeout:
        return ui["timeout_error"]
    except Exception as exc:
        return f"Error: {exc}"


def speak(text: str, ui: dict[str, str]) -> bool:
    if platform.system() != "Darwin" or not text.strip():
        return False
    command = ["say", "-r", str(int(st.session_state.speech_rate))]
    voice_name = str(st.session_state.voice_name)
    if voice_name != "System Default":
        command.extend(["-v", voice_name])
    command.append(text[:VOICE_CHAR_LIMIT])
    try:
        subprocess.Popen(command)
    except Exception as exc:
        st.session_state.last_error = f"{ui['voice_failed']}: {exc}"
    return len(text) > VOICE_CHAR_LIMIT


def chat_log_path() -> Path:
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    return CHAT_DIR / f"slimecore_chat_{st.session_state.session_log_date}.json"


def save_chat_log() -> None:
    path = chat_log_path()
    payload = {
        "session_started_at": st.session_state.session_started_at,
        "updated_at": now_label(),
        "model": st.session_state.selected_model,
        "ui_language": st.session_state.ui_language,
        "messages": st.session_state.messages,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def add_message(role: str, content: str) -> None:
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
            "time": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    save_chat_log()


def clear_chat() -> None:
    st.session_state.messages = []
    st.session_state.last_spoken_index = -1
    st.session_state.last_error = ""
    st.session_state.voice_limit_note = False
    st.session_state.session_started_at = now_label()
    st.session_state.session_log_date = today_key()
    st.session_state.input_nonce += 1
    save_chat_log()


def latest_assistant_reply() -> str:
    for item in reversed(st.session_state.messages):
        if item.get("role") == "assistant":
            return str(item.get("content", ""))
    return ""


def handle_user_prompt(user_text: str, ui: dict[str, str]) -> None:
    st.session_state.voice_limit_note = False
    add_message("user", user_text)
    reply = call_ollama(user_text, st.session_state.selected_model, ui)
    add_message("assistant", reply)
    new_index = len(st.session_state.messages) - 1
    if st.session_state.auto_voice and new_index != st.session_state.last_spoken_index:
        st.session_state.voice_limit_note = speak(reply, ui)
        st.session_state.last_spoken_index = new_index


def install_double_enter_shortcut(grace_ms: int, enabled: bool, send_label: str, confirm_label: str) -> None:
    enabled_js = "true" if enabled else "false"
    components.html(
        f"""
        <script>
        (function () {{
            const enabled = {enabled_js};
            const graceMs = {grace_ms};
            const sendLabel = {json.dumps(send_label)};
            const confirmLabel = {json.dumps(confirm_label)};
            const allSendLabels = new Set([sendLabel, confirmLabel, '送信', 'Send', 'もう一度 Enter で送信', 'Press Enter again to send']);

            const normalized = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const fireMouse = (button) => {{
                const opts = {{ bubbles: true, cancelable: true, view: window.parent }};
                for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {{
                    button.dispatchEvent(new MouseEvent(type, opts));
                }}
            }};
            const syncArea = (area) => {{
                area.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: null }}));
                area.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }};
            const findSendButton = (doc) => {{
                const buttons = Array.from(doc.querySelectorAll('button'));
                return buttons.find((button) => button.dataset.slimeSendButton === 'ready')
                    || buttons.find((button) => allSendLabels.has(normalized(button.innerText)))
                    || buttons.find((button) => button.getAttribute('kind') === 'primary')
                    || buttons.find((button) => normalized(button.innerText) === sendLabel);
            }};

            const install = () => {{
                let doc;
                try {{
                    doc = window.parent.document;
                }} catch (error) {{
                    return;
                }}
                const area = doc.querySelector('textarea[aria-label="slime_textarea"]');
                const send = findSendButton(doc);
                if (!area || !send || area.dataset.slimeDoubleEnter === 'ready') {{
                    return;
                }}

                send.dataset.slimeSendButton = 'ready';
                if (!enabled) {{
                    return;
                }}

                area.dataset.slimeDoubleEnter = 'ready';
                let lastEnterAt = 0;
                let countdownTimer = null;
                let composing = false;

                const resetButton = () => {{
                    clearInterval(countdownTimer);
                    countdownTimer = null;
                    lastEnterAt = 0;
                    send.innerText = sendLabel;
                    send.style.background = '';
                    send.style.borderColor = '';
                    send.style.color = '';
                    area.style.boxShadow = '';
                }};

                const renderCountdown = () => {{
                    const elapsed = Date.now() - lastEnterAt;
                    const remaining = Math.max(0, graceMs - elapsed);
                    const pct = Math.max(0, Math.min(100, (remaining / graceMs) * 100));
                    send.innerText = confirmLabel;
                    send.style.borderColor = 'rgba(255, 189, 102, 0.95)';
                    send.style.color = '#fff6dc';
                    send.style.background = `linear-gradient(90deg, rgba(255,189,102,0.42) ${{pct}}%, rgba(255,109,138,0.18) ${{pct}}%)`;
                    area.style.boxShadow = '0 0 0 2px rgba(255, 189, 102, 0.36)';
                    if (remaining <= 0) {{
                        resetButton();
                    }}
                }};

                const armSend = () => {{
                    clearInterval(countdownTimer);
                    lastEnterAt = Date.now();
                    renderCountdown();
                    countdownTimer = setInterval(renderCountdown, 50);
                }};

                area.addEventListener('compositionstart', () => {{ composing = true; }});
                area.addEventListener('compositionend', () => {{ composing = false; }});

                area.addEventListener('keydown', (event) => {{
                    if (event.key !== 'Enter' || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) {{
                        return;
                    }}
                    if (!area.value.trim() || send.disabled || send.getAttribute('aria-disabled') === 'true') {{
                        return;
                    }}
                    if (composing || event.isComposing || event.keyCode === 229) {{
                        return;
                    }}

                    const now = Date.now();
                    if (lastEnterAt && now - lastEnterAt < graceMs) {{
                        event.preventDefault();
                        event.stopPropagation();
                        syncArea(area);
                        resetButton();
                        window.setTimeout(() => fireMouse(send), 30);
                        return;
                    }}

                    event.preventDefault();
                    event.stopPropagation();
                    armSend();
                }}, true);

                area.addEventListener('input', () => {{
                    if (!area.value.trim()) {{
                        resetButton();
                    }}
                }});
            }};

            install();
            window.setInterval(install, 500);
        }})();
        </script>
        """,
        height=0,
    )


def render_latest_answer(waiting: bool, ui: dict[str, str]) -> None:
    if waiting:
        st.markdown(
            f"""
            <div class='latest-answer-panel latest-answer-waiting'>
                <div class='latest-answer-label'>{html.escape(ui['latest_answer'])}</div>
                <div class='latest-answer-text'>{html.escape(ui['thinking'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    latest_reply = latest_assistant_reply()
    if latest_reply:
        note = ""
        if st.session_state.voice_limit_note:
            note = f"<div class='warn-note'>{html.escape(ui['voice_limit'])}</div>"
        st.markdown(
            f"""
            <div class='latest-answer-panel'>
                <div class='latest-answer-label'>{html.escape(ui['latest_answer'])}</div>
                <div class='latest-answer-text'>{html.escape(latest_reply).replace(chr(10), '<br>')}</div>
                {note}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class='latest-answer-panel'>
                <div class='latest-answer-label'>{html.escape(ui['latest_answer'])}</div>
                <div class='small-note'>{html.escape(ui['answer_placeholder'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


init_state()

with st.sidebar:
    st.radio(
        "Language",
        ["ja", "en"],
        format_func=lambda code: "日本語" if code == "ja" else "English",
        horizontal=True,
        key="ui_language",
    )

ui = get_ui_text(st.session_state.ui_language)
ollama_online, installed_models, ollama_message = get_installed_models(ui)
model_options = ordered_models(installed_models)
active_model = choose_model(model_options)

cpu = psutil.cpu_percent(interval=0.08)
mem = psutil.virtual_memory().percent
voice_ready = platform.system() == "Darwin"
processing = bool(st.session_state.processing_prompt)

with st.sidebar:
    st.markdown("<div class='sidebar-title'>SLIME CORE</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sidebar-copy'>{html.escape(ui['sidebar_copy'])}</div>", unsafe_allow_html=True)
    if ASSET_PATH.exists():
        st.image(str(ASSET_PATH), width="stretch")

    if model_options:
        st.session_state.selected_model = st.selectbox(
            ui["model_label"],
            model_options,
            index=model_options.index(active_model),
            disabled=processing,
        )
    else:
        st.session_state.selected_model = st.text_input(ui["model_label"], value=active_model, disabled=processing)

    st.session_state.temperature = st.slider("temperature", 0.0, 1.2, float(st.session_state.temperature), 0.05, disabled=processing)
    st.session_state.num_predict = st.slider(ui["max_response"], 96, 1024, int(st.session_state.num_predict), 32, disabled=processing)

    st.divider()
    st.session_state.enter_submit_enabled = st.toggle(ui["enter_toggle"], value=bool(st.session_state.enter_submit_enabled), disabled=processing)
    st.session_state.enter_grace_secs = st.slider(ui["enter_grace"], 1.0, 3.0, float(st.session_state.enter_grace_secs), 0.1, disabled=processing)

    st.divider()
    st.session_state.auto_voice = st.toggle(ui["auto_voice"], value=bool(st.session_state.auto_voice), disabled=processing)
    voices = get_macos_voice_options()
    voice_index = voices.index(st.session_state.voice_name) if st.session_state.voice_name in voices else 0
    st.session_state.voice_name = st.selectbox("voice", voices, index=voice_index, disabled=processing)
    st.session_state.speech_rate = st.slider(ui["speech_rate"], 120, 240, int(st.session_state.speech_rate), 5, disabled=processing)

    st.divider()
    if st.button(ui["clear_chat"], width="stretch", disabled=processing):
        clear_chat()
        st.rerun()

    status_class = "pill-ok" if ollama_online else "pill-bad"
    voice_class = "pill-ok" if voice_ready else "pill-warn"
    st.markdown(
        f"""
        <div class='status-row'>
            <span class='pill {status_class}'>{html.escape(ollama_message)}</span>
            <span class='pill {voice_class}'>{html.escape(ui['voice_ready'] if voice_ready else ui['voice_unavailable'])}</span>
            <span class='pill'>CPU {cpu:.0f}%</span>
            <span class='pill'>MEM {mem:.0f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{html.escape(ui['active_model'])}</div>
            <div class='metric-value'>{html.escape(st.session_state.selected_model)}</div>
            <br>
            <div class='metric-label'>{html.escape(ui['voice'])}</div>
            <div class='metric-value'>{html.escape(str(st.session_state.voice_name))} / {int(st.session_state.speech_rate)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not ollama_online:
        st.markdown(f"<div class='warn-note'>{html.escape(ollama_message)}</div>", unsafe_allow_html=True)

chat_tab, kobun_tab = st.tabs([ui["chat_tab"], ui["kobun_tab"]])

with chat_tab:
    st.markdown(f"<div class='main-title'>{html.escape(ui['main_title'])}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='main-subtitle'>{html.escape(ui['main_subtitle'])}</div>", unsafe_allow_html=True)

    title_col, send_col, replay_col, save_col = st.columns([1.3, 0.72, 1.12, 0.92])
    with title_col:
        st.markdown(f"<div class='composer-heading'>{html.escape(ui['comment'])}</div>", unsafe_allow_html=True)
    with send_col:
        send_btn = st.button(ui["send"], type="primary", width="stretch", disabled=processing, key="slime_send_button")
    with replay_col:
        if st.button(ui["read_last"], width="stretch", disabled=processing):
            for message in reversed(st.session_state.messages):
                if message["role"] == "assistant":
                    st.session_state.voice_limit_note = speak(message["content"], ui)
                    break
    with save_col:
        if st.button(ui["save_log"], width="stretch", disabled=processing):
            save_chat_log()
            st.toast(ui["saved"])

    st.markdown(f"<div class='composer-help'>{html.escape(ui['composer_help'])}</div>", unsafe_allow_html=True)
    draft_key = f"draft_prompt_{st.session_state.input_nonce}"
    draft_prompt = st.text_area(
        "slime_textarea",
        key=draft_key,
        height=110,
        placeholder=ui["placeholder"],
        label_visibility="collapsed",
        disabled=processing,
    )

    install_double_enter_shortcut(
        grace_ms=int(float(st.session_state.enter_grace_secs) * 1000),
        enabled=bool(st.session_state.enter_submit_enabled),
        send_label=ui["send"],
        confirm_label=ui["send_again"],
    )

    if send_btn and draft_prompt.strip() and not processing:
        st.session_state.processing_prompt = draft_prompt.strip()
        st.session_state.input_nonce += 1
        st.rerun()

    render_latest_answer(waiting=processing, ui=ui)

    if processing:
        prompt_to_process = st.session_state.processing_prompt
        with st.spinner(ui["thinking"]):
            handle_user_prompt(prompt_to_process, ui)
        st.session_state.processing_prompt = ""
        st.rerun()

    st.markdown(f"<div class='chat-log-title'>{html.escape(ui['chat_log'])}</div>", unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown(f"<p class='small-note'>{html.escape(ui['empty_log'])}</p>", unsafe_allow_html=True)
    elif has_omitted_messages():
        st.markdown(f"<p class='small-note'>{html.escape(ui['omitted'])}</p>", unsafe_allow_html=True)

    for message in visible_messages():
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            st.caption(message.get("time", ""))

with kobun_tab:
    render_kobun_panel(
        app_dir=str(APP_DIR),
        default_model=st.session_state.selected_model,
        ui_language=st.session_state.ui_language,
    )
