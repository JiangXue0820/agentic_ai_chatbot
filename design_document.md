# === PROJECT ANALYSIS PROMPT ===
You are a senior software architect reviewing this repository.

Your task:
Perform a **deep architecture and code analysis** of the entire project in this repository.

---

## 🎯 Goal
Generate a **technical architecture report** suitable for inclusion in the README.md of a coding assignment titled:
> "Agentic AI API with Memory and External Integrations"

The goal is to summarize:
- System architecture and design
- Core components and how they interact
- Functional call flow
- Memory integration
- External API connections (Gmail, Weather, Vector DB)
- Security, logging, and authentication
- Optional web UI (Streamlit or Gradio)
- **System-level call graphs for the test cases**

---

## 🧩 Step-by-step instructions

### 1. **Scan the repository**
- Identify the project root (e.g., `/app`, `/src`, `/backend`, `/core`, `/agent`, `/ui`).
- List all main Python modules and packages.
- Note how imports and dependencies connect modules.

### 2. **Analyze core components**
For each key area (if present):
- **Agent Logic** — how the agent reasons, routes, or plans.
- **Memory Module** — how context is stored/retrieved (e.g., database, JSON, vector store).
- **External Integrations** — detect and describe Gmail, Weather, Vector DB usage.
- **API Layer** — endpoints exposed (FastAPI, Flask, etc.), routes, and data formats.
- **UI Layer** — if using Streamlit/Gradio, describe the interaction flow.

### 3. **Map the call flow**
Explain how a user request (e.g., “Summarize my last 5 emails”) moves through the system:
- From frontend → API → agent → memory → integrations → response
- Include key functions/classes involved at each step.

### 4. **Extract design patterns and dependencies**
- Identify patterns (e.g., MVC, service layer, adapter).
- List key dependencies from `requirements.txt` or imports.
- Note async usage, caching, or concurrency patterns.

### 5. **Assess security, privacy, and logging**
- Check for token-based authentication or `.env` config.
- Look for logging, privacy filtering, or sensitive data handling.

---

## 🧱 Output Format

Produce a **Markdown-formatted architecture report**, including:

### 🏗️ System Architecture Diagram
Use Mermaid syntax (```mermaid) to visualize components:
- API layer
- Agent logic
- Memory
- Integrations (Gmail, Weather, VectorDB)
- UI and storage

### 🧠 Core Components Summary
| Component | Purpose | Key Classes/Functions | Dependencies |
|------------|----------|----------------------|---------------|

### 🔄 Functional Flow
Explain step-by-step how input → reasoning → external call → output occurs.

### 💾 Memory Design
Describe how memory is persisted and accessed.

### 🌐 External Integrations
Summarize Gmail, Weather, and VectorDB connections.

### 🔐 Security & Privacy
List any authentication, environment configs, and logging mechanisms.

### 🧩 Module Map
Show the repository’s folder structure and explain each folder’s role.

### 🧪 Test & Example Use Cases
Document example user queries and expected outputs.

---

## 📊 Generate System-level Call Graphs (Mermaid sequence diagrams)

For each of the following **test cases**, generate a clear `mermaid sequenceDiagram` showing the **function-level call flow** through the system:

### **Test Case 1 — Gmail API**
**Input:** “Summarize my last 5 emails”  
**Expected Flow:**  
User → API → Agent → Memory → Gmail Integration → Summary → Response

### **Test Case 2 — Weather API**
**Input:** “What’s the weather in Singapore?”  
**Expected Flow:**  
User → API → Agent → Weather API → Response

### **Test Case 3 — Vector DB**
**Input:** “Explain privacy-preserving federated learning”  
**Expected Flow:**  
User → API → Agent → Memory → Vector DB → Knowledge Snippet → Response

Each diagram should:
- Show main classes/functions invoked
- Indicate data direction and structure (e.g., JSON request/response)
- Be written in ```mermaid``` syntax and ready to embed in README.md

---

---

## 📋 Notes
- Keep explanations **precise, professional, and architecture-oriented**.
- Include **code references (filenames, classes, key functions)** where useful.
- If multiple frameworks (FastAPI + Streamlit), describe both roles.
- Use bullet points, tables, and diagrams for clarity.

---

## 🏁 Final Output
Output a complete Markdown report to `design_report.md`

---

Now start the analysis and generate the full report based on the current code repository.
