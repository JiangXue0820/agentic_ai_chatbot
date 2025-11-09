import os
import requests
import streamlit as st
from datetime import datetime

# ===============================
# Config
# ===============================
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Agentic AI Chat", layout="wide")
st.markdown(
    """
    <style>
    div[data-testid="stFileUploader"] > div > div {
        padding: 0;
    }
    div[data-testid="stFileUploaderDropzone"] {
        padding: 0;
        height: 44px;
        display: inline-flex;
        align-items: center;
    }
    div[data-testid="stFileUploaderDropzone"] label,
    div[data-testid="stFileUploaderDropzone"] small {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ===============================
# Session State Initialization
# ===============================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "secure_mode" not in st.session_state:
    st.session_state.secure_mode = False  # default OFF
if "ingested_docs" not in st.session_state:
    st.session_state.ingested_docs = {}

# ===============================
# Helper Functions
# ===============================
def call_agent_api(query: str, session_id: str, secure_mode: bool = False) -> dict | None:
    """Unified Agent API call"""
    token = st.session_state.api_token
    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.post(
            f"{API_BASE}/agent/invoke",
            json={
                "input": query,
                "session_id": session_id,
                "secure_mode": secure_mode
            },
            headers=headers,
            timeout=30,
        )

        if r.status_code != 200:
            st.error(f"❌ API Error {r.status_code}: {r.text[:200]}")
            return None
        return r.json()

    except Exception as e:
        st.error(f"❌ API call failed: {e}")
        return None


def call_login_api(username: str, password: str) -> str | None:
    """Login and get access token"""
    try:
        res = requests.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=15)
        if res.status_code == 200:
            return res.json().get("access_token")
        elif res.status_code == 401:
            st.error("❌ Invalid username or password.")
        else:
            st.error(f"⚠️ Login failed: {res.status_code}")
    except Exception as e:
        st.error(f"🔌 Login error: {e}")
    return None


def create_session(title: str | None = None):
    sid = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = title or f"New chat {len(st.session_state.sessions) + 1}"
    st.session_state.sessions[sid] = {"title": title, "messages": []}
    st.session_state.current_session = sid


def rename_session_if_first_message(sid: str, user_input: str):
    sess = st.session_state.sessions.get(sid)
    if sess and len(sess["messages"]) == 1:
        sess["title"] = user_input.strip()[:12] + ("…" if len(user_input) > 12 else "")


# ===============================
# Login Page
# ===============================
if not st.session_state.authenticated:
    st.title("🔐 Agentic AI Login")

    username = st.text_input("Username", placeholder="admin")
    password = st.text_input("Password", type="password", placeholder="••••••")

    if st.button("Login"):
        token = call_login_api(username, password)
        if token:
            st.session_state.api_token = token
            st.session_state.authenticated = True
            st.sidebar.success("✅ Login successful!")
            st.rerun()

    st.stop()

# ===============================
# Sidebar - Sessions + Config
# ===============================
st.sidebar.title("💬 Sessions")

if st.sidebar.button("➕ New Chat"):
    create_session()
    st.rerun()

for sid, sess in sorted(st.session_state.sessions.items(), reverse=True):
    active = sid == st.session_state.current_session
    title = sess["title"]
    if st.sidebar.button(f"{'🟢' if active else '⚪'} {title}", key=f"s_{sid}"):
        st.session_state.current_session = sid
        st.rerun()

st.sidebar.divider()

# 🧩 User Config
st.sidebar.subheader("👤 User Config")

with st.sidebar.expander("🔧 LLM Config", expanded=False):
    llm_provider = st.selectbox("LLM Provider", ["OpenAI", "Anthropic", "Gemini", "Local"], key="llm_provider")
    show_llm_token = st.checkbox("👁️ Show Token", key="show_llm_token")
    st.text_input(
        "LLM Token",
        type="default" if show_llm_token else "password",
        value=os.getenv(f"{llm_provider.upper()}_API_KEY", ""),
        key="llm_token"
    )

with st.sidebar.expander("📧 Gmail Config", expanded=False):
    gmail_user = st.text_input("User Account", key="gmail_user")
    show_gmail_pass = st.checkbox("👁️ Show Password", key="show_gmail_pass")
    st.text_input(
        "Password",
        type="default" if show_gmail_pass else "password",
        key="gmail_password"
    )

st.sidebar.divider()
st.sidebar.caption("⚙️ Settings")
st.sidebar.text_input("API Base", API_BASE, key="api_base")

if st.sidebar.button("Health Check"):
    try:
        r = requests.get(f"{st.session_state.api_base}/health")
        st.sidebar.success(r.json())
    except Exception as e:
        st.sidebar.error(str(e))

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.session_state.api_token = None
    st.rerun()

# ===============================
# Main Chat Window
# ===============================
st.title("🧠 Agentic AI Chat")

if not st.session_state.current_session:
    st.info("Please select a session or click ➕ to start.")
    st.stop()

sid = st.session_state.current_session
session = st.session_state.sessions[sid]
messages = session["messages"]

chat_box = st.container()
with chat_box:
    if not messages:
        st.info("💡 Let's start chatting!")
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            color = "#DCF8C6" if role == "user" else "#F0F0F0"
            align = "right" if role == "user" else "left"
            icon = "👤" if role == "user" else "🤖"
            name = "You" if role == "user" else "Agent"

            st.markdown(
                f"""
                <div style='text-align:{align};background-color:{color};
                padding:10px;border-radius:10px;margin:5px 0;max-width:80%;
                float:{align};clear:both'>
                {icon} <b>{name}:</b> {content}
                </div><div style='clear:both'></div>
                """,
                unsafe_allow_html=True,
            )

            if msg.get("masked_input"):
                st.markdown(
                    f"<div style='text-align:{align};font-size:0.8em;color:#666;font-style:italic;'>"
                    f"🔒 Protected version: {msg['masked_input']}</div>",
                    unsafe_allow_html=True,
                )

# ===============================
# Input Section
# ===============================
st.divider()

# 修复输入框重复显示上次问题
input_key = f"user_input_{sid}"
user_input = st.text_input("💬 Ask something:", placeholder="Type your question here...", key=input_key)

col_secure, col_upload, col_send, col_clear = st.columns([1.2, 1.2, 2, 1])

with col_secure:
    st.session_state.secure_mode = st.toggle("Secure", value=st.session_state.secure_mode, key="secure_toggle")

with col_upload:
    uploaded_file = st.file_uploader(
        "📄 Upload",
        type=["pdf", "txt", "docx", "md"],
        label_visibility="collapsed",
    )
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        file_key = f"{uploaded_file.name}:{len(file_bytes)}"
        if file_key in st.session_state.ingested_docs:
            st.info(f"ℹ️ {uploaded_file.name} 已上传，可重新选择文件覆盖。")
        else:
            files = {
                "file": (
                    uploaded_file.name,
                    file_bytes,
                    uploaded_file.type or "application/octet-stream",
                )
            }
            headers = {"Authorization": f"Bearer {st.session_state.api_token}"}
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                try:
                    res = requests.post(
                        f"{API_BASE}/tools/vdb/ingest",
                        headers=headers,
                        files=files,
                        timeout=120,
                    )
                    if res.status_code == 200:
                        data = res.json()
                        empty_pages = data.get("empty_pages", 0)
                        chunks = data.get("chunks")
                        message = f"✅ {uploaded_file.name} uploaded to knowledge base."
                        if chunks is not None:
                            message = f"{message} ({chunks} chunks)"
                        st.success(message)
                        if empty_pages:
                            st.info(f"ℹ️ Skipped {empty_pages} blank pages.")
                        st.session_state.ingested_docs[file_key] = datetime.now().isoformat()
                    elif res.status_code == 400:
                        detail = res.json().get("detail")
                        st.warning(detail or "⚠️ File too short or unreadable.")
                    else:
                        st.error(f"⚠️ Upload failed: {res.status_code} — {res.text[:150]}")
                except Exception as e:
                    st.error(f"❌ Upload error: {e}")

with col_send:
    send_clicked = st.button("🚀 Send", use_container_width=True, key=f"send_{sid}")

with col_clear:
    if st.button("🧹 Clear", key=f"clear_{sid}"):
        session["messages"].clear()
        st.rerun()

if send_clicked and user_input.strip():
    session["messages"].append({"role": "user", "content": user_input})
    rename_session_if_first_message(sid, user_input)

    data = call_agent_api(user_input, sid, st.session_state.secure_mode)
    if data:
        if data.get("masked_input"):
            session["messages"][-1]["masked_input"] = data["masked_input"]

        answer = data.get("answer", str(data))
        session["messages"].append({"role": "assistant", "content": answer})
        st.rerun()
    else:
        st.warning("💡 Try rephrasing your question or check the API server status")

# ===============================
# Recommended Queries
# ===============================
st.divider()
st.caption("✨ Try asking the following questions:")
query_cols = st.columns(3)
recommendations = [
    "What's the weather in Singapore?",
    "Summarize my last 5 emails",
    "Explain privacy-preserving federated learning",
]
for i, q in enumerate(recommendations):
    if query_cols[i].button(q):
        session["messages"].append({"role": "user", "content": q})
        rename_session_if_first_message(sid, q)
        data = call_agent_api(q, sid, st.session_state.secure_mode)
        if data:
            if data.get("masked_input"):
                session["messages"][-1]["masked_input"] = data["masked_input"]
            answer = data.get("answer", str(data))
            session["messages"].append({"role": "assistant", "content": answer})
            st.rerun()
        else:
            st.warning("💡 Try checking the API server or another query")
