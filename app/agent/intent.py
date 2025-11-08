# =====================================================
# app/agent/intent.py
# Intent Schema & Recognition Logic
# =====================================================

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
import json
import logging
import re
        

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
            "recall_conversation": "memory",
        }
        self.min_confidence = 0.5

    # =====================================================
    # Public API
    # =====================================================
    def recognize(self, text: str, context: List[Dict[str, str]]) -> Union[List[Intent], Dict[str, Any]]:
        """
        Use LLM to identify user intent(s).
        Returns:
          - List[Intent] if clear
          - Dict[type='clarification', message='...', options=[...]] if ambiguous
        """
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
- get_weather: Get weather information (slots: location, date, days_offset)
- summarize_emails: Summarize emails (slots: count, filter)
- query_knowledge: Search knowledge base (slots: query, topic)
- general_qa: General questions, chitchat, or any query that doesn't require tools (slots: query)
- recall_conversation: Recall previous conversation context (slots: query)

If ambiguous or uncertain, set 'ambiguous': true.
Return valid JSON with this structure:
{
  "intents": [
    {"name": "intent_name", "slots": {"key": "value"}, "confidence": 0.0-1.0}
  ],
  "ambiguous": false,
  "clarification_needed": false
}"""

            user_prompt = f"{context_str}\nCurrent query: {text}\n\nAnalyze and return JSON."

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Call LLM
            response = self.llm.chat(messages)
            logger.info(f"Intent recognition LLM response: {response[:200]}")

            # Parse JSON response
            intents = self._parse_llm_response(response, text)
            return intents

        except Exception as e:
            logger.error(f"Intent recognition failed: {e}", exc_info=True)
            # Fallback to keyword-based recognition
            return self._fallback_recognition(text)

    # =====================================================
    # Parse LLM response
    # =====================================================
    def _parse_llm_response(self, response: str, original_text: str) -> Union[List[Intent], Dict[str, Any]]:
        """Parse LLM JSON response into Intent objects."""
        logger = logging.getLogger(__name__)
        
        try:
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            
            ambiguous = bool(data.get("ambiguous") or data.get("clarification_needed"))
            
            intent_list = []
            for intent_data in data.get("intents", []):
                try:
                    confidence = float(intent_data.get("confidence", 0.75))
                except (TypeError, ValueError):
                    confidence = 0.75
                if confidence < self.min_confidence:
                    return {
                        "type": "clarification",
                        "message": f"Intent confidence too low ({confidence:.2f}). Please clarify your goal.",
                        "options": ["Weather", "Emails", "Knowledge search"],
                        "intents": [],
                        "steps": []
                    }
                
                intent = Intent(
                    name=intent_data.get("name", "unknown"),
                    slots=intent_data.get("slots", {}),
                    confidence=confidence,
                    priority=intent_data.get("priority", 0),
                )
                intent_list.append(intent)
            
            if ambiguous and intent_list and all(i.confidence >= self.min_confidence for i in intent_list):
                ambiguous = False

            if ambiguous:
                return {
                    "type": "clarification",
                    "message": "Your request seems ambiguous. Please clarify:",
                    "options": ["Check weather", "Summarize emails", "Search knowledge base"],
                    "intents": [],
                    "steps": []
                }

            if not intent_list:
                return self._fallback_recognition(original_text)
            
            return intent_list
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return self._fallback_recognition(original_text)

    # =====================================================
    # Fallback Recognition
    # =====================================================
    def _fallback_recognition(self, text: str) -> List[Intent]:
        """Keyword-based fallback recognition."""
        text_lower = text.lower()
        
        # Weather
        weather_keywords = ["weather", "天气", "temperature", "forecast", "预报"]
        if any(kw in text_lower for kw in weather_keywords):
            location = "Singapore"
            in_match = re.search(r'\b(?:in|at)\s+([A-Z][a-z]+)', text)
            if in_match:
                location = in_match.group(1)
            days_offset = 0
            if "tomorrow" in text_lower or "明天" in text_lower:
                days_offset = 1
            elif "yesterday" in text_lower or "昨天" in text_lower:
                days_offset = -1
            slots = {"location": location, "days_offset": days_offset}
            return [Intent("get_weather", slots, 0.8)]
        
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
        
        # Conversation recall keywords
        recall_keywords = [
            "what did i ask",
            "previous chat",
            "之前问过",
            "之前说",
            "history",
            "conversation before",
        ]
        if any(kw in text_lower for kw in recall_keywords):
            return [Intent(
                name="recall_conversation",
                slots={"query": text},
                confidence=0.8,
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
