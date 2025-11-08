# =====================================================
# app/agent/intent.py
# Intent Schema & Recognition Logic
# =====================================================

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class Intent:
    name: str
    slots: Dict[str, Any]
    confidence: float
    priority: int = 0
    needs_confirmation: bool = False
    clarification_prompt: Optional[str] = None


class IntentRecognizer:
    """
    Encapsulates LLM-based intent classification logic.
    """

    def __init__(self, llm):
        self.llm = llm
        # Intent→Tool mapping hints
        self.intent_tool_hints = {
            "get_weather": "weather",
            "check_weather": "weather",
            "weather_query": "weather",
            "summarize_emails": "gmail",
            "read_emails": "gmail",
            "check_emails": "gmail",
            "query_knowledge": "vdb",
            "search_knowledge": "vdb",
            "general_qa": None,  # No tool needed - direct LLM chat
        }

    def recognize(self, text: str, context: List[Dict[str, str]]) -> List[Intent] | Dict:
        """
        Use LLM to identify user intent(s).
        Returns:
          - List[Intent] if clear
          - Dict[type='clarification', message='...', options=[...]] if ambiguous
        """
        import json
        import logging
        import re
        
        logger = logging.getLogger(__name__)
        
        try:
            # Build context string from conversation history
            context_str = ""
            if context:
                context_str = "\nConversation history:\n"
                for msg in context[-3:]:  # Last 3 turns
                    context_str += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"

            # Create structured JSON prompt for LLM
            system_prompt = """You are an intent recognition assistant. Analyze the user's query and return a JSON response.

Available intents:
- get_weather: Get weather information (slots: location)
- summarize_emails: Summarize emails (slots: count, filter)
- query_knowledge: Search knowledge base for specific documents (slots: query, topic)
- general_qa: General questions, chitchat, or any query that doesn't require tools (slots: query)

Use general_qa for:
- General knowledge questions
- Explanations that don't require searching documents
- Greetings, chitchat
- Questions that can be answered directly by the LLM

Return valid JSON with this structure:
{
  "intents": [
    {
      "name": "intent_name",
      "slots": {"key": "value"},
      "confidence": 0.0-1.0
    }
  ],
  "ambiguous": false,
  "clarification_needed": false
}

If the query is ambiguous or confidence is low, set ambiguous=true."""

            user_prompt = f"{context_str}\nCurrent query: {text}\n\nAnalyze the intent and return JSON."

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Call LLM
            response = self.llm.chat(messages)
            logger.info(f"Intent recognition LLM response: {response[:200]}")

            # Parse JSON response
            intents = self._parse_llm_response(response, text)
            
            if isinstance(intents, dict) and intents.get("type") == "clarification":
                return intents
            
            return intents

        except Exception as e:
            logger.error(f"Intent recognition failed: {e}", exc_info=True)
            # Fallback to keyword-based recognition
            return self._fallback_recognition(text)

    def _parse_llm_response(self, response: str, original_text: str) -> List[Intent] | Dict:
        """Parse LLM JSON response into Intent objects."""
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            
            # Check if clarification needed
            if data.get("ambiguous") or data.get("clarification_needed"):
                return {
                    "type": "clarification",
                    "message": "您的问题不太明确，请选择您想要的操作：",
                    "options": [
                        "查询天气信息",
                        "查看邮件摘要",
                        "搜索知识库"
                    ]
                }
            
            # Parse intents
            intent_list = []
            for intent_data in data.get("intents", []):
                confidence = float(intent_data.get("confidence", 0.5))
                
                # Check confidence threshold
                if confidence < 0.7:
                    return {
                        "type": "clarification",
                        "message": f"我不太确定您的意图（置信度: {confidence:.2f}），请更详细地描述您的需求。",
                        "options": ["查询天气", "查看邮件", "搜索知识"]
                    }
                
                intent = Intent(
                    name=intent_data.get("name", "unknown"),
                    slots=intent_data.get("slots", {}),
                    confidence=confidence,
                    priority=intent_data.get("priority", 0),
                )
                intent_list.append(intent)
            
            if not intent_list:
                # No intents recognized, use fallback
                return self._fallback_recognition(original_text)
            
            return intent_list
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return self._fallback_recognition(original_text)

    def _fallback_recognition(self, text: str) -> List[Intent]:
        """Keyword-based fallback recognition."""
        import re
        
        text_lower = text.lower()
        
        # Weather keywords
        weather_keywords = ["weather", "天气", "temperature", "温度", "forecast", "预报"]
        if any(kw in text_lower for kw in weather_keywords):
            # Extract location
            location = "Singapore"  # default
            # Simple location extraction
            for word in text.split():
                if word and len(word) > 2 and word[0].isupper():
                    location = word
                    break
            
            return [Intent(
                name="get_weather",
                slots={"location": location},
                confidence=0.75,
                priority=0
            )]
        
        # Email keywords
        email_keywords = ["email", "邮件", "gmail", "inbox", "收件箱", "summarize"]
        if any(kw in text_lower for kw in email_keywords):
            count = 5  # default
            # Extract count
            numbers = re.findall(r'\d+', text)
            if numbers:
                count = int(numbers[0])
            
            return [Intent(
                name="summarize_emails",
                slots={"count": count},
                confidence=0.75,
                priority=0
            )]
        
        # General knowledge/QA keywords (don't require document search)
        qa_keywords = ["explain", "what", "how", "why", "tell me", "解释", "什么是", "怎么", "为什么"]
        if any(kw in text_lower for kw in qa_keywords):
            return [Intent(
                name="general_qa",
                slots={"query": text},
                confidence=0.75,
                priority=0
            )]
        
        # Document search keywords (require VDB)
        search_keywords = ["search", "find", "查找", "搜索"]
        if any(kw in text_lower for kw in search_keywords):
            return [Intent(
                name="query_knowledge",
                slots={"query": text},
                confidence=0.70,
                priority=0
            )]
        
        # Default to general_qa for unknown queries
        return [Intent(
            name="general_qa",
            slots={"query": text},
            confidence=0.6,
            priority=0
        )]
