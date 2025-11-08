import os
import requests
import streamlit as st
from datetime import datetime

# ===============================
# Config
# ===============================
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Agentic AI Chat", layout="wide")

# ===============================
# Session State 初始化
# ===============================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "current_session" not in st.session_state:
    st.session_state.current_session = None

# ===============================
# Helper Functions
# ===============================
def call_agent_api(query: str, session_id: str) -> dict | None:
    """统一封装 Agent API 调用与错误处理"""
    token = st.session_state.api_token
    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.post(
            f"{API_BASE}/agent/invoke",
            json={"input": query, "session_id": session_id},
            headers=headers,
            timeout=30,
        )

        if r.status_code != 200:
            st.error(f"❌ API Error {r.status_code}: {r.text[:200]}")
            return None

        try:
            return r.json()
        except ValueError:
            st.error(f"❌ Invalid JSON response: {r.text[:200]}")
            return None

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timeout - Agent took too long to respond")
    except requests.exceptions.ConnectionError:
        st.error(f"🔌 Connection error - Is the API running at {API_BASE}?")
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 Network error: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
    return None


def call_login_api(username: str, password: str) -> str | None:
    """调用 /auth/login 并返回 access_token"""
    try:
        res = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("access_token")
        elif res.status_code == 401:
            st.error("❌ Invalid username or password.")
        else:
            st.error(f"⚠️ Login failed: {res.status_code}")
    except Exception as e:
        st.error(f"🔌 Login error: {e}")
    return None


def create_session(title: str | None = None):
    """创建新会话"""
    sid = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = title or f"New chat {len(st.session_state.sessions) + 1}"
    st.session_state.sessions[sid] = {"title": title, "messages": []}
    st.session_state.current_session = sid


def rename_session_if_first_message(sid: str, user_input: str):
    """第一次提问后自动设置标题"""
    sess = st.session_state.sessions.get(sid)
    if sess and len(sess["messages"]) == 1:
        title = user_input.strip()[:12] + ("…" if len(user_input) > 12 else "")
        sess["title"] = title


# ===============================
# 登录界面
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

    st.stop()  # 不渲染主界面，直接停在登录页

# ===============================
# Sidebar - Session List
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
st.sidebar.caption("⚙️ Settings")
st.sidebar.text_input("API Base", API_BASE, key="api_base")

# Health Check
if st.sidebar.button("Health Check"):
    try:
        r = requests.get(f"{st.session_state.api_base}/health")
        st.sidebar.success(r.json())
    except Exception as e:
        st.sidebar.error(str(e))

# Logout
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

# ===============================
# Input Area
# ===============================
st.divider()
user_input = st.text_input("💬 Ask something:", placeholder="Type your question here...")

col_send, col_clear = st.columns([3, 1])
with col_send:
    send_clicked = st.button("🚀 Send", use_container_width=True)
with col_clear:
    if st.button("🧹 Clear Session"):
        session["messages"].clear()
        st.rerun()

if send_clicked and user_input.strip():
    session["messages"].append({"role": "user", "content": user_input})
    rename_session_if_first_message(sid, user_input)

    data = call_agent_api(user_input, sid)
    if data:
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
        data = call_agent_api(q, sid)
        if data:
            answer = data.get("answer", str(data))
            session["messages"].append({"role": "assistant", "content": answer})
            st.rerun()
        else:
            st.warning("💡 Try checking the API server or another query")
