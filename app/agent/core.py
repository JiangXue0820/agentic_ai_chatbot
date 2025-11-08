# =====================================================
# app/agent/core.py
# Agent Orchestrator — Final English Version
# Integrated with LongTermMemoryStore and ReAct planning
# =====================================================

from typing import List, Dict, Any, Optional
from dataclasses import asdict
from datetime import datetime
import logging
import json

from app.llm.provider import LLMProvider
from app.tools.weather import WeatherAdapter
from app.tools.gmail import GmailAdapter
from app.tools.vdb import VDBAdapter
from app.memory.sqlite_store import SQLiteStore
from app.agent.intent import Intent, IntentRecognizer
from app.agent.toolkit import ToolRegistry
from app.agent.memory import ShortTermMemory, SessionMemory, LongTermMemoryStore
from app.agent.planning import Step, PlanTrace

logger = logging.getLogger(__name__)


class Agent:
    """
    Main Agent orchestrator.

    Responsibilities:
      - Intent recognition (LLM-based)
      - ReAct-style planning with max_rounds safety
      - Tool invocation via ToolRegistry
      - Memory integration (short, session, long-term)
      - Clarification and resume handling
      - Natural language summarization
    """

    def __init__(self, max_rounds: int = 6, short_mem_limit: int = 5):
        # === Core Modules ===
        self.llm = LLMProvider()
        self.intent_recognizer = IntentRecognizer(self.llm)

        # === Tool Registry ===
        self.tools = ToolRegistry({
            "weather": WeatherAdapter(),
            "gmail": GmailAdapter(),
            "vdb": VDBAdapter(),
        })

        # === Memory Systems ===
        self.mem = SQLiteStore()
        self.short_mem = ShortTermMemory(limit=short_mem_limit)
        self.session_mem = SessionMemory(self.mem)
        self.longterm_mem = LongTermMemoryStore()

        # === Safety Control ===
        self.max_rounds = max_rounds

    # =====================================================
    # === Public API ===
    # =====================================================

    def handle(self, user_id: str, text: str, session_id: str = "default") -> Dict:
        """
        Main entry point for processing a user query.
        Pipeline:
          1. Load short-term and session context
          2. Retrieve long-term recall
          3. Recognize intents (clarify if needed)
          4. Plan and execute
          5. Update memories
          6. Return structured output
        """
        logger.info(f"Handling query for user {user_id}: {text[:100]}")

        # === 1. Load memory context ===
        context = self.short_mem.get_context()
        session_ctx = self.session_mem.read(user_id, session_id, "context")

        session_data = {}
        if isinstance(session_ctx, list) and len(session_ctx) > 0:
            session_ctx = session_ctx[-1].get("content", "{}")
        try:
            if isinstance(session_ctx, str):
                session_data = json.loads(session_ctx)
        except Exception as e:
            logger.warning(f"Failed to parse session context: {e}")

        # === 2. Retrieve long-term recall ===
        longterm_context = self.longterm_mem.search(text, top_k=3)
        merged_context = self._merge_context(context, longterm_context)

        # === 3. Intent recognition ===
        intents = self._recognize_intents(text, merged_context)
        if isinstance(intents, dict) and intents.get("type") == "clarification":
            pending_context = {
                "clarification_type": "intent_ambiguous",
                "original_query": text,
                "pending_intents": [],
                "pending_steps": [],
                "timestamp": datetime.now().isoformat()
            }
            self.session_mem.write(user_id, session_id, "pending_context", json.dumps(pending_context))
            logger.info("Saved pending context for intent clarification")
            return intents

        # === 4. Plan and execute ===
        result = self._plan_and_execute(user_id, text, intents, merged_context)
        if result.get("type") == "clarification":
            result["steps"] = result.get("steps", [])
            result["intents"] = [asdict(i) for i in intents] if isinstance(intents, list) else []
            pending_context = {
                "clarification_type": "tool_failed",
                "original_query": text,
                "pending_intents": result["intents"],
                "pending_steps": result["steps"],
                "timestamp": datetime.now().isoformat()
            }
            self.session_mem.write(user_id, session_id, "pending_context", json.dumps(pending_context))
            return result

        # === 5. Update memories ===
        self.short_mem.add("user", text)
        self.short_mem.add("assistant", result.get("answer", ""))

        session_data = {
            "last_intents": [asdict(i) for i in intents] if isinstance(intents, list) else [],
            "last_steps": result.get("steps", []),
            "conversation_history": context,
            "clarification_pending": None
        }
        self.session_mem.write(user_id, session_id, "context", json.dumps(session_data), None)

        snapshot = self.session_mem.to_longterm_snapshot(user_id, session_id)
        if snapshot:
            self.longterm_mem.store_conversation(user_id, session_id, snapshot)

        logger.info("Memory updated successfully.")
        return result

    def resume(self, user_id: str, user_reply: str, session_id: str = "default") -> Dict:
        """
        Called when user answers a clarification prompt.
        Resumes execution using the saved pending context.
        """
        logger.info(f"Resuming conversation for {user_id}: {user_reply[:80]}")

        try:
            context_data = self.session_mem.read(user_id, session_id, "pending_context")
            if not context_data:
                return {"type": "answer", "answer": "No pending clarification found. Please start a new query."}

            context_json = json.loads(context_data) if isinstance(context_data, str) else context_data
            clarification_type = context_json.get("clarification_type", "")
            original_query = context_json.get("original_query", "")

            if clarification_type == "intent_ambiguous":
                context = self.short_mem.get_context()
                context.append({"role": "user", "content": user_reply})
                intents = self._recognize_intents(user_reply, context)
                self.session_mem.write(user_id, session_id, "pending_context", None)
                return self._plan_and_execute(user_id, user_reply, intents, context)

            elif clarification_type == "tool_failed":
                if "retry" in user_reply.lower():
                    self.session_mem.write(user_id, session_id, "pending_context", None)
                    return self.handle(user_id, original_query, session_id)
                else:
                    self.session_mem.write(user_id, session_id, "pending_context", None)
                    return {"type": "answer", "answer": "Okay, operation cancelled. Anything else I can help with?"}

            else:
                self.session_mem.write(user_id, session_id, "pending_context", None)
                return self.handle(user_id, user_reply, session_id)

        except Exception as e:
            logger.error(f"Resume failed: {e}", exc_info=True)
            return {"type": "answer", "answer": f"An error occurred while resuming: {e}"}

    # =====================================================
    # === Internal Methods ===
    # =====================================================

    def _recognize_intents(self, text: str, context: List[Dict[str, str]]) -> List[Intent] | Dict:
        """Use LLM to identify structured intents."""
        try:
            result = self.intent_recognizer.recognize(text, context)
            if isinstance(result, dict) and result.get("type") == "clarification":
                return result
            if isinstance(result, list):
                return result
            return {
                "type": "clarification",
                "message": "I’m not sure what you mean. Please clarify:",
                "options": ["Check weather", "Read emails", "Search knowledge base"]
            }
        except Exception as e:
            logger.error(f"Intent recognition failed: {e}", exc_info=True)
            return {
                "type": "clarification",
                "message": "An error occurred while interpreting your request.",
                "options": ["Retry", "Rephrase"]
            }

    def _plan_and_execute(
        self, user_id: str, user_query: str, intents: List[Intent], context: List[Dict[str, str]]
    ) -> Dict:
        """Main ReAct-style reasoning and tool execution loop."""
        steps, used_tools, citations, observations = [], [], [], []
        trace = PlanTrace(user_query=user_query)  

        for intent in intents:
            round_count = 0
            done = False

            while not done and round_count < self.max_rounds:
                round_count += 1
                step = self._plan_next_step(intent, user_query, steps, observations, context)
                if not step:
                    done = True
                    break

                if step.action and step.action != "finish":
                    try:
                        observation = self.tools.invoke(step.action, **step.input)
                        step.observation = observation
                        step.status = "succeeded"
                        obs_str = self._format_observation(observation)
                        observations.append(obs_str)
                        used_tools.append({
                            "name": step.action,
                            "inputs": step.input,
                            "outputs": observation,
                            "status": "succeeded"
                        })
                    except Exception as e:
                        step.status = "failed"
                        trace.add_step(step)  # ✅ record even failed step
                        return {
                            "type": "clarification",
                            "message": f"Tool {step.action} failed: {e}. Retry?",
                            "options": ["Retry", "Cancel"],
                            "steps": [asdict(s) for s in steps],
                            "intents": [asdict(i) for i in intents],
                            "trace": trace.to_dict()  # ✅ new field
                        }
                elif intent.name == "general_qa":
                    qa_response = self._direct_llm_qa(user_query, context)
                    step.observation = {"answer": qa_response}
                    step.status = "succeeded"
                    observations.append(qa_response)

                trace.add_step(step)   # ✅ replaces steps.append(step)
                steps.append(step)     # keep legacy list for backward compatibility

                if step.status == "finished" or step.action == "finish" or not step.decide_next:
                    done = True

            if round_count >= self.max_rounds:
                return {
                    "type": "answer",
                    "answer": "I reached the reasoning limit but couldn't complete the task. Please restate your question.",
                    "intents": [asdict(i) for i in intents],
                    "steps": [asdict(s) for s in steps],
                    "used_tools": used_tools,
                    "citations": citations,
                    "trace": trace.to_dict(),  
                }

        answer = self._summarize_result(user_query, steps, observations)
        return {
            "type": "answer",
            "answer": answer,
            "intents": [asdict(i) for i in intents],
            "steps": [asdict(s) for s in steps],
            "used_tools": used_tools,
            "citations": citations,
            "trace": trace.to_dict(),  
        }

    # =====================================================
    # === Planning Logic (Step-related)
    # =====================================================

    def _plan_next_step(
        self, intent: Intent, user_query: str, previous_steps: List[Step],
        observations: List[str], context: List[Dict[str, str]]
    ) -> Optional[Step]:
        """Use LLM to plan the next reasoning step."""
        try:
            tool_info = self.tools.describe()
            system_prompt = f"""
You are a reasoning assistant that plans step-by-step actions to complete user intents.
You have access to these tools:
{json.dumps(tool_info, indent=2)}

Respond in JSON:
{{
  "thought": "your reasoning on what to do next",
  "action": "tool_name or 'finish'",
  "input": {{ "param": "value" }},
  "decide_next": true/false
}}
"""
            steps_context = ""
            if previous_steps:
                for i, step in enumerate(previous_steps[-3:], 1):
                    steps_context += f"{i}. {step.action} ({step.status})\n"

            user_prompt = f"""
User query: {user_query}
Current intent: {intent.name}
Slots: {json.dumps(intent.slots)}
Previous steps:
{steps_context}
Recent observations:
{observations[-3:] if observations else []}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = self.llm.chat(messages)
            return self._parse_planning_response(response, intent)

        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)
            return self._fallback_planning(intent)

    def _parse_planning_response(self, response: str, intent: Intent) -> Optional[Step]:
        """Parse LLM planning output into a Step object."""
        try:
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            data = json.loads(json_str)
            return Step(
                intent=intent.name,
                thought=data.get("thought", ""),
                action=data.get("action"),
                input=data.get("input", {}),
                observation=None,
                status="planned",
                decide_next=bool(data.get("decide_next", False)),
            )
        except Exception as e:
            logger.warning(f"Failed to parse planning response: {e}")
            return self._fallback_planning(intent)

    def _fallback_planning(self, intent: Intent) -> Step:
        """Fallback when planning fails."""
        mapping = {
            "get_weather": ("weather", {"city": intent.slots.get("location", "Singapore")}),
            "summarize_emails": ("gmail", {"count": intent.slots.get("count", 5)}),
            "query_knowledge": ("vdb", {"query": intent.slots.get("query", "")}),
            "general_qa": (None, {"query": intent.slots.get("query", "")}),
        }
        action, inputs = mapping.get(intent.name, (None, {"query": ""}))
        inputs = {k: v for k, v in inputs.items() if v}
        return Step(
            intent=intent.name,
            thought=f"Fallback planning: {intent.name} → {action or 'direct LLM'}",
            action=action,
            input=inputs,
            observation=None,
            status="planned",
            decide_next=False,
        )

    # =====================================================
    # === Summarization & Helpers
    # =====================================================

    def _format_observation(self, observation: Any) -> str:
        """Format tool output for readability."""
        if isinstance(observation, dict):
            if "results" in observation and isinstance(observation["results"], list):
                if not observation["results"]:
                    return "No relevant results found."
                return f"Found {len(observation['results'])} relevant items."
            if "temperature" in observation:
                loc = observation.get("location", "")
                return f"Weather in {loc}: {observation['temperature']}°C, {observation.get('condition', '')}"
            return str(observation)
        return str(observation)[:300]

    def _direct_llm_qa(self, user_query: str, context: List[Dict[str, str]]) -> str:
        """Direct QA mode (no tool invocation)."""
        try:
            system_prompt = (
                "You are a helpful assistant. Answer naturally and clearly in the same language as the user."
            )
            messages = [{"role": "system", "content": system_prompt}]
            messages += context[-6:]
            messages.append({"role": "user", "content": user_query})
            return self.llm.chat(messages)
        except Exception as e:
            logger.error(f"Direct QA failed: {e}", exc_info=True)
            return f"Sorry, an error occurred: {e}"

    def _summarize_result(self, user_query: str, steps: List[Step], observations: List[str]) -> str:
        """Use LLM to summarize final answer."""
        if not observations:
            return "I couldn't find relevant information for your question."
        system_prompt = (
            "You are a helpful assistant. Combine the gathered information into a clear, natural summary."
        )
        summary_context = f"User query: {user_query}\n\n" + "\n".join(observations[-5:])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": summary_context},
        ]
        try:
            return self.llm.chat(messages)
        except Exception as e:
            logger.error(f"Summarization failed: {e}", exc_info=True)
            return self._format_fallback_answer(user_query, observations)

    def _format_fallback_answer(self, user_query: str, observations: List[str]) -> str:
        """Fallback answer when summarization fails."""
        if not observations:
            return "No information available."
        return "Based on the gathered information:\n" + "\n".join(f"- {obs}" for obs in observations[-5:])

    def _merge_context(self, short_context: List[Dict[str, str]], longterm_context: List[Dict[str, Any]]):
        """Merge short-term context with semantic long-term memory."""
        merged = list(short_context)
        if longterm_context:
            memory_summary = "\n".join([f" Previous memory: {c['chunk']}" for c in longterm_context])
            merged.append({"role": "system", "content": memory_summary})
        return merged
