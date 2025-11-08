import os, requests, streamlit as st

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("API_TOKEN", "changeme")

st.set_page_config(page_title="Agentic AI MVP", layout="centered")
st.title("Agentic AI – Demo UI")

headers = {"Authorization": f"Bearer {API_TOKEN}"}

with st.sidebar:
    st.text_input("API Base", API_BASE, key="api_base")
    st.text_input("Bearer Token", API_TOKEN, key="api_token")
    if st.button("Health Check"):
        r = requests.get(f"{st.session_state.api_base}/health")
        st.write(r.json())

prompt = st.text_input("Ask the agent", value="Summarize my last 5 emails")
if st.button("Send"):
    r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": prompt}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
    st.json(r.json())

st.subheader("Quick Tests")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Gmail: last 5"):
        r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": "Summarize my last 5 emails"}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
        st.json(r.json())
with col2:
    if st.button("Weather: Singapore"):
        r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": "What's the weather in Singapore?"}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
        st.json(r.json())
with col3:
    if st.button("VDB: PPFL"):
        r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": "Explain privacy-preserving federated learning"}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
        st.json(r.json())

