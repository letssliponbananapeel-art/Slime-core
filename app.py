import base64
import datetime
import html
import platform
import subprocess
from pathlib import Path

import psutil
import requests
import streamlit as st

OLLAMA_HOST = "http://localhost:11434"
CHAT_API = f"{OLLAMA_HOST}/api/chat"
TAGS_API = f"{OLLAMA_HOST}/api/tags"
DEFAULT_MODEL = "gemma4:26b"
REQUEST_TIMEOUT = 240
MAX_LOGS = 80

SCRIPT_DIR = Path(__file__).resolve().parent
DESKTOP_ASSET_DIR = Path.home() / "Desktop" / "スライムコア"
LOCAL_ASSET_DIR = SCRIPT_DIR / "スライムコア"
ASSET_DIR = LOCAL_ASSET_DIR if LOCAL_ASSET_DIR.exists() else DESKTOP_ASSET_DIR

CHAR_IMAGE_FILES = {
    "idle": ASSET_DIR / "スライムコア9.jpeg",
    "happy": ASSET_DIR / "スライムコア4.jpeg",
    "angry": ASSET_DIR / "スライムコア2.jpeg",
    "sad": ASSET_DIR / "スライムコア7.jpeg",
    "fun": ASSET_DIR / "スライムコア5.jpeg",
}

st.set_page_config(
    page_title="SLIME CORE",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    background-color: #04070f !important;
    color: #a7ffe6 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 12px !important;
}
.block-container {
    padding: 0.55rem 0.8rem 0.8rem 0.8rem !important;
    max-width: 760px !important;
}
h1,h2,h3 {
    font-family: 'Orbitron', sans-serif !important;
    color: #00e6a0 !important;
    letter-spacing: 0.06em;
    margin: 0.15rem 0 0.3rem 0 !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #03110d 0%, #04100d 100%) !important;
    border-right: 1px solid rgba(0,230,160,0.14) !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
[data-testid="stSidebar"] .block-container {
    padding: 0.55rem 0.65rem 0.75rem 0.65rem !important;
}
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
    background-color: #071612 !important;
    color: #baffec !important;
    border: 1px solid rgba(0,230,160,0.24) !important;
    border-radius: 4px !important;
    min-height: 34px !important;
}
.stButton > button {
    background: transparent !important;
    color: #00e6a0 !important;
    border: 1px solid #00e6a0 !important;
    border-radius: 4px !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 11px !important;
    padding: 0.25rem 0.2rem !important;
    min-height: 34px !important;
}
.stButton > button:hover { background: rgba(0,230,160,0.08) !important; }
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #071512 0%, #081b16 100%) !important;
    border: 1px solid rgba(0,230,160,0.15) !important;
    border-left: 3px solid #00e6a0 !important;
    border-radius: 6px !important;
    padding: 0.45rem 0.55rem !important;
}
[data-testid="stMetricLabel"] { color: #4dffbf !important; font-size: 0.58rem !important; }
[data-testid="stMetricValue"] {
    color: #00ffb3 !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.95rem !important;
}
.stProgress { height: 10px !important; }
.stProgress > div > div {
    background: linear-gradient(90deg, #00e6a0, #33c7ff) !important;
}
.section-header {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.62rem;
    color: #4dffbf;
    letter-spacing: 0.16em;
    border-bottom: 1px solid rgba(0,230,160,0.14);
    padding-bottom: 0.22rem;
    margin: 0.35rem 0 0.45rem 0;
}
.panel, .log-panel, .response-panel, .char-panel {
    background: #03070d;
    border: 1px solid rgba(0,230,160,0.12);
    border-radius: 8px;
    padding: 0.42rem 0.5rem;
}
.response-panel {
    min-height: 96px;
    line-height: 1.65;
    font-size: 0.74rem;
}
.log-panel {
    min-height: 96px;
    max-height: 96px;
    overflow-y: auto;
    font-size: 0.66rem;
    line-height: 1.45;
}
.log-line { font-size: 0.68rem; line-height: 1.55; }
.log-info { color: #66ffd0; }
.log-warn { color: #ffd44d; }
.log-error { color: #ff6464; }
.log-sys { color: #72c7ff; }
.status-badge {
    display:inline-block;
    padding:0.18rem 0.65rem;
    border-radius:4px;
    font-family:'Orbitron', sans-serif;
    font-size:0.62rem;
    letter-spacing:0.12em;
}
.badge-ok { color:#00ffb3; border:1px solid #00ffb3; background:rgba(0,255,179,0.08); }
.badge-warn { color:#ffd44d; border:1px solid #ffd44d; background:rgba(255,212,77,0.08); }
.badge-crit { color:#ff5555; border:1px solid #ff5555; background:rgba(255,85,85,0.08); }
.badge-idle { color:#72c7ff; border:1px solid #72c7ff; background:rgba(114,199,255,0.08); }
.small-note { font-size: 0.64rem; color: #84e7c7; opacity: 0.78; }
.mini { font-size: 0.62rem; opacity: 0.72; }
.chat-box {
    padding: 0.42rem 0.55rem;
    margin: 0.28rem 0;
    border-radius: 0 5px 5px 0;
    font-size: 0.73rem;
}
.chat-user {
    background: #0b1d18;
    border-left: 3px solid #00e6a0;
    border: 1px solid rgba(0,230,160,0.16);
}
.chat-ai {
    background: #091017;
    border-left: 3px solid #33c7ff;
    border: 1px solid rgba(51,199,255,0.14);
}
.chat-label {
    font-size: 0.52rem;
    opacity: 0.6;
    margin-bottom: 0.12rem;
    letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)

defaults = {
    "chat_history": [],
    "log_lines": [],
    "emotion": "idle",
    "temperature": 0.18,
    "num_predict": 220,
    "selected_model": DEFAULT_MODEL,
    "system_prompt": "あなたは自然で親しみやすい日本語アシスタントです。必ず自然な日本語で、簡潔に、1〜4文で答えてください。考え中の内容は出さず、最終回答だけ返してください。",
    "clear_chat_input_nonce": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")

def add_log(msg, level="INFO"):
    css_map = {"INFO":"log-info","WARN":"log-warn","ERROR":"log-error","SYS":"log-sys"}
    css = css_map.get(level, "log-info")
    st.session_state.log_lines.append(
        f'<span class="log-line {css}">[{ts()}] [{level}] {html.escape(str(msg))[:220]}</span>'
    )
    st.session_state.log_lines = st.session_state.log_lines[-MAX_LOGS:]

def image_file_to_data_uri(path: Path) -> str:
    try:
        if path.exists():
            return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception:
        pass
    return ""

def detect_emotion(text: str) -> str:
    if any(k in text for k in ["ごめん", "申し訳", "できません", "不明", "見つから", "接続でき", "タイムアウト"]):
        return "sad"
    if any(k in text for k in ["危険", "警告", "失敗", "エラー", "問題"]):
        return "angry"
    if any(k in text for k in ["やった", "うれしい", "ありがとう", "最高", "成功", "よかった"]):
        return "happy"
    if any(k in text for k in ["面白", "楽しい", "わくわく", "いいね", "かわいい"]):
        return "fun"
    return "idle"

def get_system_state(cpu_pct: float, mem_pct: float):
    if mem_pct >= 90 or cpu_pct >= 90:
        return "HEAVY", "badge-crit", "かなり重い"
    if mem_pct >= 80 or cpu_pct >= 75:
        return "BUSY", "badge-warn", "少し重い"
    if mem_pct >= 60 or cpu_pct >= 45:
        return "NORMAL", "badge-ok", "普通"
    return "LIGHT", "badge-idle", "軽い"

def check_ollama():
    try:
        res = requests.get(TAGS_API, timeout=10)
        res.raise_for_status()
        data = res.json()
        models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        return True, models
    except Exception:
        return False, []

def build_messages(user_prompt: str, history: list[dict], system_prompt: str) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt.strip()}]
    for item in history[-6:]:
        role = "user" if item["role"] == "user" else "assistant"
        messages.append({"role": role, "content": item["text"]})
    messages.append({"role": "user", "content": user_prompt})
    return messages

def extract_reply(data: dict) -> str:
    msg = data.get("message", {}) or {}
    content = (msg.get("content") or "").strip()
    if content:
        return content
    return ""

def speak_mac(text: str):
    try:
        subprocess.Popen(["say", "-r", "185", text[:500]])
    except Exception:
        pass

def ollama_chat(messages: list[dict], model: str, temperature: float, num_predict: int):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        }
    }
    try:
        res = requests.post(CHAT_API, json=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        content = extract_reply(data)
        if not content:
            return "最終回答をうまく受け取れなかった。もう一度短く聞いて。", data
        return content, data
    except requests.exceptions.Timeout:
        return "応答が遅い。26bでも重いときがある。質問を短くしてみて。", {}
    except requests.exceptions.ConnectionError:
        return "Ollamaに接続できない。`ollama serve` を確認して。", {}
    except Exception as e:
        return f"エラー: {e}", {}

cpu_pct = psutil.cpu_percent(interval=0.10)
mem = psutil.virtual_memory()
disk = psutil.disk_usage("/")
boot_ts = datetime.datetime.fromtimestamp(psutil.boot_time())
uptime = datetime.datetime.now() - boot_ts
state_label, badge_cls, state_text = get_system_state(cpu_pct, mem.percent)
ollama_ok, available_models = check_ollama()

if available_models and st.session_state.selected_model not in available_models:
    if DEFAULT_MODEL in available_models:
        st.session_state.selected_model = DEFAULT_MODEL
    else:
        st.session_state.selected_model = available_models[0]

add_log(f"Ollama {'online' if ollama_ok else 'offline'} / models={len(available_models)}", "SYS")
add_log(f"CPU {cpu_pct:.1f}% / MEM {mem.percent:.1f}% / DISK {disk.percent:.1f}%", "INFO")

with st.sidebar:
    st.markdown("### 🤖 SLIME CORE")
    st.markdown("<div class='section-header'>CHAT</div>", unsafe_allow_html=True)

    chat_key = f"user_input_{st.session_state.clear_chat_input_nonce}"
    user_input = st.text_input("入力", placeholder="話しかける…", label_visibility="collapsed", key=chat_key)
    c1, c2 = st.columns(2)
    with c1:
        send_btn = st.button("SEND", use_container_width=True)
    with c2:
        clear_btn = st.button("CLEAR", use_container_width=True)

    if clear_btn:
        st.session_state.chat_history = []
        st.session_state.clear_chat_input_nonce += 1
        add_log("履歴をクリア", "SYS")
        st.rerun()

    st.markdown("<div class='section-header'>MODEL</div>", unsafe_allow_html=True)
    preferred_order = ["gemma4:26b", "gemma4:31b", "gemma4:e4b", "gemma4:e2b"]
    display_models = [m for m in preferred_order if m in available_models] + [m for m in available_models if m not in preferred_order]
    if display_models:
        idx = display_models.index(st.session_state.selected_model) if st.session_state.selected_model in display_models else 0
        st.session_state.selected_model = st.selectbox("model", display_models, index=idx, label_visibility="collapsed")
    else:
        st.session_state.selected_model = st.text_input("model", value=st.session_state.selected_model, label_visibility="collapsed")
    st.markdown("<div class='mini'>26b を既定に変更済み</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>TUNING</div>", unsafe_allow_html=True)
    st.session_state.temperature = st.slider("temperature", 0.0, 1.0, st.session_state.temperature, 0.05)
    st.session_state.num_predict = st.slider("num_predict", 64, 768, st.session_state.num_predict, 32)

    st.markdown("<div class='section-header'>SYSTEM INFO</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='small-note'>
        Ollama: {"接続中" if ollama_ok else "未接続"}<br>
        モデル: {html.escape(st.session_state.selected_model)}<br>
        CPU: {cpu_pct:.1f}% / MEM: {mem.percent:.1f}%<br>
        状態: {html.escape(state_text)}<br>
        画像: {html.escape(str(ASSET_DIR))}
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<h1>SLIME CORE</h1>", unsafe_allow_html=True)
st.markdown(
    f"<div class='small-note'>MODEL: {html.escape(st.session_state.selected_model)} | {ts()} | {html.escape(state_text)}</div>",
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns([1.4, 1, 1, 1])
with m1:
    st.metric("MODEL", st.session_state.selected_model)
with m2:
    st.metric("CPU", f"{cpu_pct:.1f}%")
with m3:
    st.metric("MEM", f"{mem.percent:.1f}%")
with m4:
    st.metric("STATE", state_text)

bar1, bar2, bar3 = st.columns(3)
with bar1:
    st.progress(int(cpu_pct))
with bar2:
    st.progress(int(mem.percent))
with bar3:
    st.progress(int(disk.percent))

if send_btn and user_input.strip():
    user_text = user_input.strip()
    st.session_state.chat_history.append({"role": "user", "text": user_text})
    add_log(f"input: {user_text[:80]}", "SYS")
    messages = build_messages(
        user_prompt=user_text,
        history=st.session_state.chat_history[:-1],
        system_prompt=st.session_state.system_prompt,
    )
    with st.spinner("thinking"):
        response, meta = ollama_chat(
            messages=messages,
            model=st.session_state.selected_model,
            temperature=st.session_state.temperature,
            num_predict=st.session_state.num_predict,
        )
    st.session_state.chat_history.append({"role": "slime", "text": response})
    st.session_state.emotion = detect_emotion(response)
    speak_mac(response)
    st.session_state.clear_chat_input_nonce += 1
    add_log(f"reply done / {st.session_state.selected_model}", "SYS")
    st.rerun()

st.markdown("<div class='section-header'>RESPONSE</div>", unsafe_allow_html=True)
last_reply = ""
for entry in reversed(st.session_state.chat_history):
    if entry["role"] == "slime":
        last_reply = entry["text"]
        break
safe_reply = html.escape(last_reply).replace("\n", "<br>") if last_reply else "ここに返答が出る"
st.markdown(f"<div class='response-panel'>{safe_reply}</div>", unsafe_allow_html=True)

st.markdown("<div class='section-header'>CHARACTER</div>", unsafe_allow_html=True)
img_uri = image_file_to_data_uri(CHAR_IMAGE_FILES.get(st.session_state.emotion, CHAR_IMAGE_FILES["idle"]))
if img_uri:
    char_block = f'<img src="{img_uri}" style="width:120px; max-width:100%; height:auto; image-rendering:pixelated; filter:drop-shadow(0 0 8px rgba(0,230,160,0.22));" />'
else:
    char_block = '<div style="padding:1rem 0;text-align:center;color:#ff7b7b;">画像なし</div>'
st.markdown(
    f"""
    <div class='char-panel' style='text-align:center;'>
        {char_block}
        <div style='margin-top:0.4rem;'><span class='status-badge {badge_cls}'>{html.escape(state_label)}</span></div>
        <div class='small-note' style='margin-top:0.4rem;line-height:1.55;'>
            emotion: {html.escape(st.session_state.emotion)}<br>
            state: {html.escape(state_text)}<br>
            uptime: {html.escape(str(uptime).split(".")[0])}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='section-header'>CHAT LOG</div>", unsafe_allow_html=True)
chat_html = []
for entry in st.session_state.chat_history:
    safe = html.escape(entry["text"]).replace("\n", "<br>")
    if entry["role"] == "user":
        chat_html.append(f"<div class='chat-box chat-user'><div class='chat-label'>YOU</div>{safe}</div>")
    else:
        chat_html.append(f"<div class='chat-box chat-ai'><div class='chat-label'>SLIME</div>{safe}</div>")
st.markdown(
    "<div class='panel'>" + ("".join(chat_html) if chat_html else "<div class='small-note'>まだ会話なし</div>") + "</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-header'>EVENT LOG</div>", unsafe_allow_html=True)
logs = "<br>".join(st.session_state.log_lines[-6:])
st.markdown(f"<div class='log-panel'>{logs}</div>", unsafe_allow_html=True)
st.markdown("<div class='mini'>最新6件だけ表示</div>", unsafe_allow_html=True)

st.markdown("<div class='section-header'>QUICK START</div>", unsafe_allow_html=True)
st.code(
    "cd ~/Desktop/スライムコア\n"
    "ollama pull gemma4:26b\n"
    "streamlit run slime_dash_gemma4_compact_v2.py --server.port 8502",
    language="bash",
)
