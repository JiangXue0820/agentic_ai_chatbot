import os
import requests
import streamlit as st
from datetime import datetime
import time

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
    .agent-spinner {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 8px 0;
        padding: 8px 12px;
        border-radius: 10px;
        background-color: #F0F0F0;
        max-width: 80%;
        clear: both;
    }
    .agent-spinner .loader {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(37, 99, 235, 0.2);
        border-top-color: #2563eb;
        border-radius: 50%;
        animation: spin 0.9s linear infinite;
    }
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
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
if "ingested_docs_list" not in st.session_state:
    st.session_state.ingested_docs_list = []
if "ingested_docs_loaded" not in st.session_state:
    st.session_state.ingested_docs_loaded = False
if "sessions_loaded" not in st.session_state:
    st.session_state.sessions_loaded = False
if "pending_request" not in st.session_state:
    st.session_state.pending_request = None
if "pending_session" not in st.session_state:
    st.session_state.pending_session = None
if "agent_pending" not in st.session_state:
    st.session_state.agent_pending = False
if "input_to_clear" not in st.session_state:
    st.session_state.input_to_clear = None

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


def get_api_base() -> str:
    return st.session_state.get("api_base", API_BASE)


def fetch_ingested_documents(force: bool = False):
    if not st.session_state.api_token:
        return
    if st.session_state.ingested_docs_loaded and not force:
        return
    try:
        res = requests.get(
            f"{get_api_base()}/tools/vdb/documents",
            headers={"Authorization": f"Bearer {st.session_state.api_token}"},
            timeout=15,
        )
        if res.status_code == 200:
            st.session_state.ingested_docs_list = res.json().get("documents", [])
            st.session_state.ingested_docs_loaded = True
        else:
            st.sidebar.warning(f"⚠️ Failed to fetch document list: {res.text[:120]}")
    except Exception as exc:
        st.sidebar.warning(f"⚠️ Error fetching document list: {exc}")


def delete_ingested_document(doc_id: str) -> bool:
    try:
        res = requests.delete(
            f"{get_api_base()}/tools/vdb/document/{doc_id}",
            headers={"Authorization": f"Bearer {st.session_state.api_token}"},
            timeout=15,
        )
        if res.status_code == 200:
            st.session_state.ingested_docs_list = [
                doc for doc in st.session_state.ingested_docs_list if doc.get("doc_id") != doc_id
            ]
            return True
        if res.status_code == 404:
            st.sidebar.warning("⚠️ Document not found or already deleted")
        else:
            st.sidebar.error(f"❌Failed to delete document: {res.text[:120]}")
    except Exception as exc:
        st.sidebar.error(f"❌ Error in deleting document: {exc}")
    return False


def truncate_filename(name: str, limit: int = 20) -> str:
    return name if len(name) <= limit else f"{name[:limit]}…"


def bootstrap_user_state():
    if not st.session_state.api_token or st.session_state.sessions_loaded:
        return

    headers = {"Authorization": f"Bearer {st.session_state.api_token}"}
    try:
        res = requests.get(
            f"{get_api_base()}/admin/bootstrap",
            headers=headers,
            timeout=20,
        )
        if res.status_code != 200:
            st.sidebar.warning("⚠️ Failed to load history.")
            return

        data = res.json()
        sessions_payload = data.get("sessions") or []
        sessions: dict[str, dict] = {}
        for sess in sessions_payload:
            sid = sess.get("id")
            if not sid:
                continue
            title = (sess.get("title") or "").strip() or f"Chat {len(sessions) + 1}"
            messages = sess.get("messages") or []
            sessions[sid] = {"title": title, "messages": messages}

        st.session_state.sessions = sessions
        if sessions:
            if st.session_state.current_session not in sessions:
                st.session_state.current_session = next(iter(sessions))
        else:
            st.session_state.current_session = None

        documents = data.get("documents")
        if documents is not None:
            st.session_state.ingested_docs_list = documents
            st.session_state.ingested_docs_loaded = True

        st.session_state.sessions_loaded = True

    except Exception as exc:
        st.sidebar.warning(f"⚠️ Unable to load history: {exc}")


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
            # force reload of sessions/documents
            st.session_state.sessions_loaded = False
            bootstrap_user_state()
            st.sidebar.success("✅ Login successful!")
            st.rerun()

    st.stop()

# Ensure historical data is loaded after authentication
if st.session_state.authenticated and not st.session_state.sessions_loaded:
    bootstrap_user_state()

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

st.sidebar.subheader("📁 User Documents")
if st.session_state.api_token:
    fetch_ingested_documents()
    if st.sidebar.button("🔄 Refresh", key="refresh_docs"):
        fetch_ingested_documents(force=True)
    documents = st.session_state.ingested_docs_list
    if not documents:
        st.sidebar.caption("No documents found.")
    else:
        for doc in documents:
            name = truncate_filename(doc.get("filename", doc.get("doc_id", "")))
            uploaded_at = doc.get("uploaded_at", "")
            col_name, col_time, col_action = st.sidebar.columns([3, 2, 1])
            col_name.markdown(f"**{name}**")
            col_time.markdown(f"<small>{uploaded_at}</small>", unsafe_allow_html=True)
            if col_action.button("🗑️", key=f"del_{doc.get('doc_id')}"):
                if delete_ingested_document(doc.get("doc_id", "")):
                    st.sidebar.success("✅ Document is deleted.")
                    st.rerun()
else:
    st.sidebar.caption("Login to manage documents.")

st.sidebar.divider()
st.sidebar.caption("⚙️ Settings")
st.sidebar.text_input("API Base", API_BASE, key="api_base")

if st.sidebar.button("Health Check"):
    try:
        r = requests.get(f"{st.session_state.api_base}/health")
        st.sidebar.success(r.json())
    except Exception as e:
        st.sidebar.error(str(e))

if st.session_state.api_token and st.sidebar.button("🧨 Reset Data"):
    try:
        res = requests.post(
            f"{st.session_state.api_base}/admin/reset",
            headers={"Authorization": f"Bearer {st.session_state.api_token}"},
            timeout=60,
        )
        if res.status_code == 200:
            st.sidebar.success("✅ All data cleared.")
            token = st.session_state.api_token
            current_api_base = st.session_state.get("api_base", API_BASE)
            st.session_state.clear()
            st.session_state.api_token = token
            st.session_state.authenticated = True
            st.session_state.api_base = current_api_base
            st.session_state.sessions_loaded = False
            st.rerun()
        else:
            st.sidebar.error(f"❌ Reset failed: {res.text[:120]}")
    except Exception as exc:
        st.sidebar.error(f"❌ Reset error: {exc}")

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

        if st.session_state.agent_pending and st.session_state.pending_session == sid:
            st.markdown(
                "<div class='agent-spinner'><div class='loader'></div><span>Agent is thinking...</span></div>",
                unsafe_allow_html=True,
            )

# ===============================
# Input Section
# ===============================
st.divider()

# 修复输入框重复显示上次问题
input_key = f"user_input_{sid}"

if st.session_state.get("input_to_clear") == sid:
    st.session_state[input_key] = ""
    st.session_state.input_to_clear = None

user_input = st.text_input("💬 Ask something:", placeholder="Type your question here...", key=input_key)

col_secure, col_send, col_clear, col_upload = st.columns([0.5, 1, 1, 2])

with col_secure:
    st.session_state.secure_mode = st.toggle("Secure", value=st.session_state.secure_mode, key="secure_toggle")

with col_send:
    send_clicked = st.button("🚀 Send", use_container_width=True, key=f"send_{sid}")

with col_clear:
    clear_clicked = st.button("🧹 Clear", key=f"clear_{sid}")

if "doc_upload_reset" not in st.session_state:
    st.session_state.doc_upload_reset = False

if st.session_state.doc_upload_reset:
    if "doc_upload" in st.session_state:
        del st.session_state["doc_upload"]
    st.session_state.doc_upload_reset = False

with col_upload:
    uploaded_file = st.file_uploader(
        "📄 Upload",
        type=["pdf", "txt", "docx", "md"],
        label_visibility="collapsed",
        key="doc_upload",
    )
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        file_key = f"{uploaded_file.name}:{len(file_bytes)}"
        if file_key in st.session_state.ingested_docs:
            st.info(f"ℹ️ {uploaded_file.name} is already listed under User Documents.")
            st.session_state.doc_upload_reset = True
            st.rerun()
        else:
            files = {
                "file": (
                    uploaded_file.name,
                    file_bytes,
                    uploaded_file.type or "application/octet-stream",
                )
            }
            headers = {"Authorization": f"Bearer {st.session_state.api_token}"}
            with st.spinner(f"Processing {uploaded_file.name}..."):
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
                        st.success(message)
                        if empty_pages:
                            st.info(f"ℹ️ Skipped {empty_pages} blank pages.")
                        st.session_state.ingested_docs[file_key] = datetime.now().isoformat()
                        doc_id = data.get("doc_id")
                        uploaded_at = data.get("uploaded_at")
                        if doc_id and uploaded_at:
                            st.session_state.ingested_docs_loaded = False
                            fetch_ingested_documents(force=True)
                        st.session_state.doc_upload_reset = True
                        time.sleep(1) 
                        st.rerun()
                    elif res.status_code == 400:
                        detail = res.json().get("detail")
                        st.warning(detail or "⚠️ File too short or unreadable.")
                    else:
                        st.error(f"⚠️ Upload failed: {res.status_code} — {res.text[:150]}")
                except Exception as e:
                    st.error(f"❌ Upload error: {e}")
                    st.session_state.doc_upload_reset = True
                    st.rerun()

if clear_clicked:
    session["messages"].clear()
    st.session_state.agent_pending = False
    st.session_state.pending_request = None
    st.session_state.pending_session = None
    st.rerun()

if send_clicked and user_input.strip():
    clean_input = user_input.strip()
    session["messages"].append({"role": "user", "content": clean_input})
    rename_session_if_first_message(sid, clean_input)
    st.session_state.input_to_clear = sid
    st.session_state.pending_request = clean_input
    st.session_state.pending_session = sid
    st.session_state.agent_pending = True
    st.rerun()

if (
    st.session_state.agent_pending
    and st.session_state.pending_request
    and st.session_state.pending_session == sid
):
    query = st.session_state.pending_request
    data = call_agent_api(query, sid, st.session_state.secure_mode)
    if data:
        if data.get("masked_input"):
            session["messages"][-1]["masked_input"] = data["masked_input"]

        answer = data.get("answer", str(data))
        session["messages"].append({"role": "assistant", "content": answer})
    else:
        st.warning("💡 Try rephrasing your question or check the API server status")
    st.session_state.agent_pending = False
    st.session_state.pending_request = None
    st.session_state.pending_session = None
    st.rerun()

# ===============================
# Recommended Queries
# ===============================
st.divider()
st.caption("✨ Try asking the following questions:")
query_cols = st.columns(3)
recommendations = [
    "What's the weather in Singapore?",
    "Summarize my last 5 emails",
    "Explain the main idea of transformer models",
]
for i, q in enumerate(recommendations):
    if query_cols[i].button(q):
        session["messages"].append({"role": "user", "content": q})
        rename_session_if_first_message(sid, q)
        st.session_state.pending_request = q
        st.session_state.pending_session = sid
        st.session_state.agent_pending = True
        st.rerun()
