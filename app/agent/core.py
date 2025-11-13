# =====================================================
# app/agent/core.py
# Agent Orchestrator — Final English Version
# Integrated with LongTermMemoryStore and ReAct planning
# =====================================================

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
from datetime import datetime
import logging
import json

from app.llm.provider import LLMProvider
from app.tools.weather import WeatherAdapter
from app.tools.gmail import GmailAdapter
from app.tools.vdb import VDBAdapter
from app.tools.memory import ConversationMemoryAdapter
from app.memory.sqlite_store import SQLiteStore
from app.agent.intent import Intent, IntentRecognizer
from app.agent.toolkit import ToolRegistry
from app.agent.memory import ShortTermMemory, SessionMemory, LongTermMemoryStore
from app.agent.planning import Step, PlanTrace
from app.guardrails.security_guard import SecurityGuard

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
        self.guard = SecurityGuard()

        # === Memory Systems ===
        self.mem = SQLiteStore()
        self.short_mem = ShortTermMemory(limit=short_mem_limit)
        self.session_mem = SessionMemory(self.mem)
        self.longterm_mem = LongTermMemoryStore()

        # === Tool Registry ===
        self.tools = ToolRegistry({
            "weather": WeatherAdapter(),
            "gmail": GmailAdapter(),
            "vdb": VDBAdapter(),
            "memory":ConversationMemoryAdapter(self.longterm_mem)
        })

        # === Safety Control ===
        self.max_rounds = max_rounds

    # =====================================================
    # === Public API ===
    # =====================================================
    def _secure_inbound(self, text: str) -> str:
        """
        Secure inbound text by validating and sanitizing.
        """
        masked_input = text
        check = self.guard.inbound(text)
        if not check["safe"]:
            # Unsafe query, blocked before processing
            return {
                "type": "answer",
                "answer": check["text"],
                "secure_mode": True,
                "masked_input": None,
                "intents": [],
                "steps": [],
                "used_tools": [],
                "citations": [],
            }
        masked_input = check["text"]
        return masked_input

    def _secure_outbound(self, result: Dict) -> Dict:
        """
        Secure outbound text by validating and sanitizing.
        """
        if "answer" not in result:
            return result

        answer = result["answer"]

        # inbound had masked PII
        if getattr(self.guard, "mask_map", None):
            # unmask known placeholders
            for original, mask in self.guard.mask_map.items():
                answer = answer.replace(mask, original)

        # mask new PII if any
        result["answer"] = self.guard.outbound(answer)["text"]
        result["secure_mode"] = True

        # reset for next round
        self.guard.mask_map.clear()
        return result


    def handle(self, user_id: str, text: str, session_id: str = "default", secure_mode: bool = False) -> Dict:
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

        if secure_mode:
            masked_input = self._secure_inbound(text)
            if isinstance(masked_input, dict) and masked_input.get("type") == "answer":
                return masked_input
            text = masked_input

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
        try:
            longterm_context = self.longterm_mem.search(
                text,
                top_k=3,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"Long-term memory search failed: {e}", exc_info=True)
            longterm_context = []
        merged_context = self._merge_context(context, longterm_context)

        # === 3. Intent recognition ===
        intents = self._recognize_intents(text, merged_context)
        logger.debug(f"Recognized intents: {intents}")
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

        if isinstance(intents, list) and intents and all(i.name == "note_down" for i in intents):
            info_text = intents[0].slots.get("text") or text
            acknowledgment = "OK, I have noted the information down."

            self.short_mem.add("user", info_text)
            self.short_mem.add("assistant", acknowledgment)
            updated_context = self.short_mem.get_context()

            prev_saved = session_data.get("longterm_saved", 0)

            note_session_data = {
                "last_intents": [asdict(i) for i in intents],
                "last_steps": [],
                "conversation_history": updated_context,
                "clarification_pending": None,
                "longterm_saved": len(updated_context),
            }
            self.session_mem.write(user_id, session_id, "context", json.dumps(note_session_data), None)

            if prev_saved < len(updated_context):
                new_messages = updated_context[prev_saved:]
                self.longterm_mem.store_conversation(
                    user_id,
                    session_id,
                    new_messages,
                    start_index=prev_saved,
                )

            return {
                "type": "answer",
                "answer": acknowledgment,
                "intents": [asdict(i) for i in intents],
                "steps": [],
                "used_tools": [],
                "citations": [],
                "trace": PlanTrace(user_query=text).to_dict(),
            }

        # === 4. Plan and execute ===
        result = self._plan_and_execute(user_id, text, intents, merged_context, session_id)
        logger.debug(f"Plan and execute result: {result.get('type')} | steps={len(result.get('steps', []))}")
        
        # Ensure result has answer field
        if not result.get("answer"):
            if result.get("type") == "clarification":
                result["answer"] = result.get("message", "Sorry, I don't understand your question.")
            else:
                result["answer"] = "Sorry, I encountered an issue while processing your request. Please try again."
        
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
        try:
            self.short_mem.add("user", text)
            self.short_mem.add("assistant", result.get("answer", ""))
        except Exception as e:
            logger.error(f"Failed to update short-term memory: {e}", exc_info=True)

        updated_context = self.short_mem.get_context()
        prev_saved = session_data.get("longterm_saved", 0)

        session_data = {
            "last_intents": [asdict(i) for i in intents] if isinstance(intents, list) else [],
            "last_steps": result.get("steps", []),
            "conversation_history": updated_context,
            "clarification_pending": None,
            "longterm_saved": len(updated_context)
        }
        
        try:
            self.session_mem.write(user_id, session_id, "context", json.dumps(session_data), None)
        except Exception as e:
            logger.error(f"Failed to write session memory: {e}", exc_info=True)

        try:
            if prev_saved < len(updated_context):
                new_messages = updated_context[prev_saved:]
                self.longterm_mem.store_conversation(user_id, session_id, new_messages, start_index=prev_saved)
        except Exception as e:
            logger.error(f"Failed to store long-term memory: {e}", exc_info=True)

        logger.info("Memory updated successfully.")

        if secure_mode and "answer" in result:
            result = self._secure_outbound(result)
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
                return self._plan_and_execute(user_id, user_reply, intents, context, session_id)

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
        self, user_id: str, user_query: str, intents: List[Intent], context: List[Dict[str, str]], session_id: str
    ) -> Dict:
        """Main ReAct-style reasoning and tool execution loop."""
        steps, used_tools, citations, observations = [], [], [], []
        trace = PlanTrace(user_query=user_query)  

        for intent in intents:
            round_count = 0
            done = False
            logger.debug(f"Starting intent loop: {intent.name} with slots={intent.slots}")

            intent_context = context
            memory_results: List[Dict[str, Any]] = []
            memory_hits_only = False
            if getattr(intent, "memory_hint", False):
                memory_query = intent.slots.get("query") or user_query
                try:
                    memory_results = self.longterm_mem.search(
                        memory_query,
                        top_k=3,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    if memory_results:
                        intent_context = self._merge_context(context, memory_results)
                        observations.append(self._format_observation({
                            "scope": "longterm",
                            "results": memory_results
                        }))
                        memory_hits_only = True
                except Exception as e:
                    logger.error(f"Long-term memory search failed: {e}", exc_info=True)

            while not done and round_count < self.max_rounds:
                round_count += 1
                step = self._plan_next_step(intent, user_query, steps, observations, intent_context)
                logger.debug(f"Planned step: {step}")
                if not step:
                    done = True
                    break

                step.memory_used = bool(getattr(intent, "memory_hint", False) and memory_results)

                if step.action and step.action != "finish":
                    if (
                        step.action == "vdb"
                        and memory_hits_only
                        and intent.name == "query_knowledge"
                    ):
                        query = intent.slots.get("query") or user_query
                        answer = self._direct_llm_qa(query, intent_context)
                        step.thought += " | Memory satisfied query; skipped VDB."
                        step.action = "memory_only"
                        step.observation = {
                            "answer": answer,
                            "memory_results": memory_results,
                        }
                        step.status = "succeeded"
                        step.decide_next = False
                        step.memory_used = True
                        observations.append(answer)
                        trace.add_step(step)
                        steps.append(step)
                        break
                    if step.action == "memory":
                        step.input.setdefault("user_id", user_id)
                        step.input.setdefault("session_id", session_id)
                    try:
                        observation = self.tools.invoke(step.action, **step.input)
                        logger.debug(f"Tool '{step.action}' observation: {observation}")
                        step.observation = observation
                        if isinstance(observation, dict) and observation.get("error"):
                            error_msg = observation.get("error", "Unknown error")
                            step.status = "failed"
                            step.error = error_msg
                            used_tools.append({
                                "name": step.action,
                                "inputs": step.input,
                                "outputs": observation,
                                "status": "failed"
                            })
                            trace.add_step(step)
                            steps.append(step)
                            logger.info(f"Tool {step.action} returned error: {error_msg}")
                            return {
                                "type": "clarification",
                                "message": f"Tool {step.action} returned an error: {error_msg}. Retry?",
                                "options": ["Retry", "Cancel"],
                                "steps": [asdict(s) for s in steps],
                                "intents": [asdict(i) for i in intents],
                                "trace": trace.to_dict()
                            }
                        if step.action == "vdb" and isinstance(observation, dict) and not observation.get("results"):
                            logger.info("Knowledge search returned no results; falling back to direct LLM QA.")
                            fallback_answer = self._direct_llm_qa(user_query, intent_context)
                            observations.append("Knowledge search returned no results about the question.")
                            observations.append(fallback_answer)
                            step.observation = {
                                "scope": "knowledge",
                                "results": observation.get("results", []),
                                "fallback_answer": fallback_answer,
                            }
                            step.status = "succeeded"
                            used_tools.append({
                                "name": "llm_fallback",
                                "inputs": {"query": user_query},
                                "outputs": {"answer": fallback_answer},
                                "status": "succeeded"
                            })
                            trace.add_step(step)
                            steps.append(step)
                            break
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
                        step.error = str(e)
                        logger.error(f"Tool {step.action} invocation raised exception: {e}", exc_info=True)
                        trace.add_step(step)  # ✅ record even failed step
                        return {
                            "type": "clarification",
                            "message": f"Tool {step.action} failed: {e}. Retry?",
                            "options": ["Retry", "Cancel"],
                            "steps": [asdict(s) for s in steps],
                            "intents": [asdict(i) for i in intents],
                            "trace": trace.to_dict()  # ✅ new field
                        }
                elif intent.name in ("general_qa", "potential_knowledge_qa"):
                    query = intent.slots.get("query") or user_query
                    rag_answer = None
                    retrieval_used = False
                    retrieval_payload: Optional[Dict[str, Any]] = None

                    if intent.name == "potential_knowledge_qa":
                        try:
                            retrieval_payload = self.tools.invoke("vdb", query=query, top_k=3)
                            retrieval_used = True
                            used_tools.append({
                                "name": "vdb",
                                "inputs": {"query": query, "top_k": 3},
                                "outputs": retrieval_payload,
                                "status": "succeeded"
                            })
                            results = retrieval_payload.get("results", []) if isinstance(retrieval_payload, dict) else []
                            best_score = max((float(result.get("score", 0.0)) for result in results), default=0.0)
                            if results and best_score > 0.65:
                                observations.append(self._format_observation(retrieval_payload))
                                augmented_context = list(context)
                                snippets = "\n".join(
                                    f"- {item.get('chunk', '').strip()}" for item in results[:3]
                                ).strip()
                                if snippets:
                                    augmented_context.append({
                                        "role": "system",
                                        "content": f"Relevant knowledge:\n{snippets}"
                                    })
                                rag_answer = self._direct_llm_qa(query, augmented_context)
                        except Exception as e:
                            logger.error(f"Vector DB retrieval failed: {e}", exc_info=True)
                            used_tools.append({
                                "name": "vdb",
                                "inputs": {"query": query, "top_k": 3},
                                "outputs": {"error": str(e)},
                                "status": "failed"
                            })

                    answer = rag_answer or self._direct_llm_qa(query, intent_context)
                    logger.debug(f"QA response ({intent.name}): {answer}")

                    observation_payload: Dict[str, Any] = {"answer": answer}
                    if retrieval_used and retrieval_payload:
                        observation_payload["retrieval"] = retrieval_payload

                    step.observation = observation_payload
                    step.status = "succeeded"
                    observations.append(answer)

                trace.add_step(step)   # ✅ replaces steps.append(step)
                steps.append(step)     # keep legacy list for backward compatibility

                should_continue = step.decide_next if step.action != "finish" else False
                if (
                    step.status in ("finished", "failed")
                    or step.action == "finish"
                    or not should_continue
                ):
                    done = True

            if round_count >= self.max_rounds:
                logger.warning("Max reasoning rounds reached before completion.")
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
        logger.debug(f"Final summarized answer: {answer}")
        
        # Ensure answer is not empty
        if not answer or not answer.strip():
            answer = "Sorry, I couldn't generate a proper response. Please try rephrasing your question."
        
        citation_entries = self._collect_citations(used_tools)
        if citation_entries:
            answer = self._append_citation_block(answer, citation_entries)
            citations = citation_entries
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
                decide_next=bool(data.get("decide_next", True)),
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
            "recall_conversation": ("memory", {"query": intent.slots.get("query", "")}),
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

    def _collect_citations(self, used_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect citation metadata from tool outputs."""
        citations: List[Dict[str, Any]] = []
        for tool in used_tools:
            if not isinstance(tool, dict):
                continue
            name = (tool.get("name") or "").lower()
            if name != "vdb":
                continue
            outputs = tool.get("outputs")
            if not isinstance(outputs, dict):
                continue
            results = outputs.get("results") or []
            for result in results:
                if not isinstance(result, dict):
                    continue
                metadata = result.get("metadata") or {}
                if not isinstance(metadata, dict):
                    continue
                filename = metadata.get("filename") or metadata.get("source")
                page = metadata.get("page")
                if filename:
                    citations.append({"filename": filename, "page": page})
        return citations

    def _append_citation_block(self, answer: str, citations: List[Dict[str, Any]]) -> str:
        """Append formatted citation block to the final answer."""
        unique: List[Tuple[str, Any]] = []
        seen = set()
        for citation in citations:
            filename = citation.get("filename")
            page = citation.get("page")
            key = (filename, page)
            if not filename or key in seen:
                continue
            seen.add(key)
            unique.append((filename, page))

        if not unique:
            return answer

        lines = []
        for idx, (filename, page) in enumerate(unique, 1):
            page_display = page if page not in (None, "") else "?"
            lines.append(f"{idx}. {filename}, page {page_display}")

        return answer.rstrip() + "\n\nSource:\n" + "\n".join(lines)

    def _format_observation(self, observation: Any) -> str:
        """Format tool output for readability."""
        if isinstance(observation, dict):
            if observation.get("scope") == "longterm" and isinstance(observation.get("results"), list):
                if not observation["results"]:
                    return "No prior conversation found."
                formatted = []
                for idx, item in enumerate(observation["results"][:3], 1):
                    if isinstance(item, dict):
                        snippet = item.get("chunk") or item.get("text") or json.dumps(item, ensure_ascii=False)
                    else:
                        snippet = str(item)
                    snippet = (snippet or "").strip().replace("\n", " ")
                    if len(snippet) > 200:
                        snippet = snippet[:200].rstrip() + "..."
                    formatted.append(f"{idx}. {snippet}")
                return "Conversation recall:\n" + "\n".join(formatted)
            if observation.get("scope") == "knowledge" and observation.get("fallback_answer"):
                return "Knowledge search returned no results. LLM answer: " + observation["fallback_answer"]
            if "results" in observation and isinstance(observation["results"], list):
                results_list = observation["results"]
                if not results_list:
                    return "No relevant results found."
                formatted = []
                max_items = min(len(results_list), 10)
                for idx, item in enumerate(results_list[:max_items], 1):
                    if isinstance(item, dict):
                        title = item.get("metadata", {}).get("title") if isinstance(item.get("metadata"), dict) else None
                        snippet = item.get("chunk") or item.get("text") or json.dumps(item, ensure_ascii=False)
                    else:
                        title = None
                        snippet = str(item)
                    snippet = (snippet or "").strip().replace("\n", " ")
                    if len(snippet) > 200:
                        snippet = snippet[:200].rstrip() + "..."
                    if title:
                        formatted.append(f"{idx}. {title}: {snippet}")
                    else:
                        formatted.append(f"{idx}. {snippet}")
                return "Knowledge hits:\n" + "\n".join(formatted)
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
