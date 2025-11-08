"""LLM abstraction. For MVP we implement a deterministic stub and leave hooks for real LLMs."""
from typing import List, Dict

class LLMProvider:
    def chat(self, messages: List[Dict]) -> str:
        # Minimal stub  echo last user content with a polite preface
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"(mocked-llm) {last_user}"

    def summarize(self, items: list[dict] | list[str], max_lines: int = 8) -> str:
        # Naive summarizer for MVP
        if isinstance(items, list) and items and isinstance(items[0], dict):
            subjects = [it.get("subject") or it.get("title") or str(it) for it in items][:max_lines]
            return "; ".join(subjects)
        texts = [str(x) for x in items][:max_lines]
        return "; ".join(texts)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Lightweight hash-based pseudo-embedding for MVP (replace with real embeddings later)
        def fe(s: str):
            import random
            random.seed(hash(s) & 0xffffffff)
            return [random.random() for _ in range(64)]
        return [fe(t) for t in texts]
