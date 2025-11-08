from typing import List, Dict
from app.llm.provider import LLMProvider
from app.tools.weather import WeatherAdapter
from app.tools.gmail import GmailAdapter
from app.tools.vdb import VDBAdapter
from app.memory.sqlite_store import SQLiteStore

class Agent:
    def __init__(self):
        self.llm = LLMProvider()
        self.weather = WeatherAdapter()
        self.gmail = GmailAdapter()
        self.vdb = VDBAdapter()
        self.mem = SQLiteStore()

    def handle(self, user_id: str, text: str, tools: List[str] | None = None, memory_keys: List[str] | None = None) -> Dict:
        tools = tools or ["gmail","weather","vdb"]
        steps, used, citations = [], [], []
        answer_parts = []

        t = text.lower()
        if "weather" in t and "weather" in tools:
            steps.append("weather.current")
            w = self.weather.current(city="Singapore" if "singapore" in t else None)
            used.append({"name":"weather","inputs":{"city": "Singapore" if "singapore" in t else None},"outputs":w})
            answer_parts.append(f"Weather: {w.get('temperature')}°C, humidity {w.get('humidity')}%, condition {w.get('condition')}")
            citations.append({"type":"weather","source": w.get("source"), "observed_at": w.get("observed_at")})

        if "email" in t or "gmail" in t:
            steps.append("gmail.list")
            emails = self.gmail.list_recent(limit=5)
            used.append({"name":"gmail","inputs":{"limit":5},"outputs":{"count":len(emails)}})
            summary = self.llm.summarize(emails)
            answer_parts.append(f"Emails summary: {summary}")
            citations.append({"type":"email","ids":[e["id"] for e in emails]})

        if "explain" in t or "vector" in t or "knowledge" in t:
            steps.append("vdb.query")
            res = self.vdb.query(text, top_k=3)
            used.append({"name":"vdb","inputs":{"top_k":3},"outputs":{"hits":len(res)}})
            snippet = "; ".join(ch.get("chunk")[:120] for ch in res)
            answer_parts.append(f"KB: {snippet}")
            for r in res:
                citations.append({"type":"kb","doc_id": r["doc_id"], "score": r["score"]})

        if not answer_parts:
            out = self.llm.chat([
                {"role":"system","content":"You are a helpful agent."},
                {"role":"user","content": text}
            ])
            answer_parts.append(out)

        self.mem.write(user_id, "session:default", "short", text, ttl=24*3600)

        return {
            "answer": " | ".join(answer_parts),
            "used_tools": used,
            "citations": citations,
            "steps": steps
        }
