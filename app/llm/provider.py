"""LLM abstraction with real LLM provider support."""
from typing import List, Dict
import logging
from app.utils.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified LLM provider supporting multiple backends."""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self._client = None
        self._init_provider()
    
    def _init_provider(self):
        """Initialize the selected LLM provider."""
        if self.provider == "deepseek":
            self._init_deepseek()
        elif self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "mock":
            logger.info("Using mock LLM provider")
        else:
            logger.warning(f"Unknown provider '{self.provider}', falling back to mock")
            self.provider = "mock"
    
    def _init_deepseek(self):
        """Initialize DeepSeek (uses OpenAI SDK)."""
        try:
            from openai import OpenAI
            if not settings.DEEPSEEK_API_KEY:
                raise ValueError("DEEPSEEK_API_KEY not configured")
            self._client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            logger.info(f"DeepSeek initialized with model: {settings.DEEPSEEK_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek: {e}")
            self.provider = "mock"
    
    def _init_gemini(self):
        """Initialize Google Gemini."""
        try:
            import google.generativeai as genai
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._client = genai.GenerativeModel(settings.GEMINI_MODEL)
            logger.info(f"Gemini initialized with model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.provider = "mock"
    
    def _init_openai(self):
        """Initialize OpenAI."""
        try:
            from openai import OpenAI
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured")
            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
            logger.info(f"OpenAI initialized with model: {settings.OPENAI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.provider = "mock"
    
    def chat(self, messages: List[Dict]) -> str:
        """
        Send chat messages to LLM and get response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            Response string from LLM
        """
        try:
            if self.provider == "deepseek" or self.provider == "openai":
                return self._chat_openai_compatible(messages)
            elif self.provider == "gemini":
                return self._chat_gemini(messages)
            else:
                return self._chat_mock(messages)
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return f"Error: {str(e)}"
    
    def _chat_openai_compatible(self, messages: List[Dict]) -> str:
        """Chat using OpenAI-compatible API (OpenAI, DeepSeek)."""
        model = settings.DEEPSEEK_MODEL if self.provider == "deepseek" else settings.OPENAI_MODEL
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    def _chat_gemini(self, messages: List[Dict]) -> str:
        """Chat using Google Gemini API."""
        # Convert messages to Gemini format
        # Gemini uses a simpler format, combine system + user messages
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"Instructions: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        response = self._client.generate_content(prompt)
        return response.text
    
    def _chat_mock(self, messages: List[Dict]) -> str:
        """Mock implementation for testing."""
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"(mocked-llm) {last_user}"
    
    def summarize(self, items: list[dict] | list[str], max_lines: int = 8) -> str:
        """
        Summarize a list of items.
        
        Args:
            items: List of dicts or strings to summarize
            max_lines: Maximum number of lines in summary
        
        Returns:
            Summary string
        """
        if self.provider == "mock":
            # Keep simple mock behavior
            if isinstance(items, list) and items and isinstance(items[0], dict):
                subjects = [it.get("subject") or it.get("title") or str(it) for it in items][:max_lines]
                return "; ".join(subjects)
            texts = [str(x) for x in items][:max_lines]
            return "; ".join(texts)
        
        # Use LLM for real summarization
        try:
            # Prepare items for summarization
            if isinstance(items, list) and items and isinstance(items[0], dict):
                item_strs = []
                for i, item in enumerate(items[:20], 1):  # Limit to 20 items
                    if "subject" in item:
                        item_strs.append(f"{i}. From: {item.get('from', 'Unknown')}, Subject: {item.get('subject', 'No subject')}")
                    else:
                        item_strs.append(f"{i}. {str(item)[:200]}")
            else:
                item_strs = [f"{i}. {str(x)[:200]}" for i, x in enumerate(items[:20], 1)]
            
            content = "\n".join(item_strs)
            messages = [
                {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                {"role": "user", "content": f"Please provide a brief summary of the following items in {max_lines} lines or less:\n\n{content}"}
            ]
            
            return self.chat(messages)
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback to simple concatenation
            if isinstance(items, list) and items and isinstance(items[0], dict):
                return "; ".join([str(it.get("subject") or it.get("title") or it) for it in items[:max_lines]])
            return "; ".join([str(x)[:50] for x in items[:max_lines]])
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for texts.
        
        Note: This is still using hash-based pseudo-embeddings.
        For production, consider using:
        - OpenAI embeddings API
        - sentence-transformers
        - Gemini embeddings
        """
        # Hash-based pseudo-embedding (same as before)
        def fe(s: str):
            import random
            random.seed(hash(s) & 0xffffffff)
            return [random.random() for _ in range(64)]
        return [fe(t) for t in texts]