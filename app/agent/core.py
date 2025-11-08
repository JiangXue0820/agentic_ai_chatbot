# =====================================================
# app/agent/core.py
# Agent Orchestrator — 增强版模板 (with max_rounds & natural output)
# =====================================================

from typing import List, Dict, Any, Optional, Literal
from dataclasses import asdict
import logging
import json
from app.llm.provider import LLMProvider
from app.tools.weather import WeatherAdapter
from app.tools.gmail import GmailAdapter
from app.tools.vdb import VDBAdapter
from app.memory.sqlite_store import SQLiteStore
from app.agent.intent import Intent, IntentRecognizer
from app.agent.toolkit import ToolRegistry
from app.agent.memory import ShortTermMemory, SessionMemory
from app.agent.planning import Step

logger = logging.getLogger(__name__)


class Agent:
    """
    Main Agent orchestrator.

    Responsibilities:
      - Intent recognition (LLM-based)
      - ReAct-style planning with safe max_rounds
      - Tool invocation via ToolRegistry
      - Memory integration (short/session)
      - Human-in-the-loop clarification
      - Natural language final answer
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

        # === Safety Control ===
        self.max_rounds = max_rounds

    # =====================================================
    # === Public API ===
    # =====================================================

    def handle(self, user_id: str, text: str, session_id: str = "default") -> Dict:
        """
        Main entry point for processing a user query.
        Pipeline:
        1. Load context from short/session memory
        2. Intent recognition (with possible clarification)
        3. ReAct planning & execution
        4. Update memories
        5. Return structured response
        """
        logger.info(f"Handling query for user {user_id}: {text[:100]}")
        
        # 1. Load context
        context = self.short_mem.get_context()  # history of last few turns, defined by short_mem_limit
        session_ctx = self.session_mem.read(user_id, session_id, "context")
        
        # Restore context from session if available
        if session_ctx:
            try:
                if isinstance(session_ctx, str):
                    session_data = json.loads(session_ctx)
                else:
                    session_data = session_ctx
                logger.info(f"Loaded session context with {len(session_data.get('conversation_history', []))} messages")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse session context: {e}")
                session_data = {}
        else:
            session_data = {}

        # 2. Intent recognition
        intents = self._recognize_intents(text, context)
        if isinstance(intents, dict) and intents.get("type") == "clarification":
            # Save pending context for resume
            pending_context = {
                "clarification_type": "intent_ambiguous",
                "original_query": text,
                "pending_intents": [],
                "pending_steps": [],
                "timestamp": str(json.dumps({}))  # Placeholder for now
            }
            self.session_mem.write(user_id, session_id, "pending_context", json.dumps(pending_context))
            logger.info("Saved pending context for intent clarification")
            return intents  # pause for human clarification

        # 3️⃣ Execute planning
        result = self._plan_and_execute(user_id, text, intents, context)
        if result.get("type") == "clarification":
            # Save pending context for resume
            pending_context = {
                "clarification_type": "tool_failed",
                "original_query": text,
                "pending_intents": [asdict(i) for i in intents] if isinstance(intents, list) else [],
                "pending_steps": result.get("steps", []),
                "timestamp": str(json.dumps({}))
            }
            self.session_mem.write(user_id, session_id, "pending_context", json.dumps(pending_context))
            logger.info("Saved pending context for tool failure clarification")
            return result  # triggered clarification mid-process

        # 4️⃣ Update memory
        self.short_mem.add("user", text)
        self.short_mem.add("assistant", result.get("answer", ""))
        
        # Serialize and save session context
        session_data = {
            "last_intents": [asdict(i) for i in intents] if isinstance(intents, list) else [],
            "last_steps": result.get("steps", []),
            "conversation_history": context,
            "clarification_pending": None
        }
        self.session_mem.write(user_id, session_id, "context", json.dumps(session_data), None)
        
        # Write to SQLite for long-term storage (24 hour TTL)
        self.mem.write(user_id, session_id, "short", text, 86400)
        
        logger.info("Updated memories successfully")

        # 5️⃣ Return final structured output
        return result

    def resume(self, user_id: str, user_reply: str, session_id: str = "default") -> Dict:
        """
        Called when user answers a clarification prompt.
        Should update the pending intent/step and continue execution.
        """
        logger.info(f"Resuming conversation for user {user_id}, reply: {user_reply[:50]}")
        
        try:
            # Load pending context from session memory
            context_data = self.session_mem.read(user_id, session_id, "pending_context")
            
            if not context_data:
                logger.warning("No pending context found for resume")
                return {
                    "type": "answer",
                    "answer": "抱歉，我找不到待处理的对话上下文。请重新开始对话。"
                }
            
            # Parse context data
            try:
                if isinstance(context_data, str):
                    context_json = json.loads(context_data)
                else:
                    context_json = context_data
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse context data: {e}")
                return {
                    "type": "answer",
                    "answer": "抱歉，对话上下文数据损坏。请重新开始对话。"
                }
            
            # Extract pending information
            clarification_type = context_json.get("clarification_type", "unknown")
            original_query = context_json.get("original_query", "")
            pending_intents = context_json.get("pending_intents", [])
            pending_steps = context_json.get("pending_steps", [])
            
            logger.info(f"Resuming with clarification_type: {clarification_type}")
            
            # Handle different clarification types
            if clarification_type == "intent_ambiguous":
                # User provided clarification for ambiguous intent
                # Re-recognize intent with the new reply as context
                context = self.short_mem.get_context()
                context.append({"role": "user", "content": user_reply})
                
                intents = self._recognize_intents(user_reply, context)
                
                if isinstance(intents, dict) and intents.get("type") == "clarification":
                    # Still ambiguous, return clarification again
                    return intents
                
                # Clear pending context and execute with new intents
                self.session_mem.write(user_id, session_id, "pending_context", None)
                result = self._plan_and_execute(user_id, user_reply, intents, context)
                
                # Update memories
                self.short_mem.add("user", user_reply)
                self.short_mem.add("assistant", result.get("answer", ""))
                
                return result
                
            elif clarification_type == "tool_failed":
                # User chose to retry or abandon
                if "重试" in user_reply or "retry" in user_reply.lower():
                    # Retry the original query
                    self.session_mem.write(user_id, session_id, "pending_context", None)
                    return self.handle(user_id, original_query, session_id)
                else:
                    # Abandon
                    self.session_mem.write(user_id, session_id, "pending_context", None)
                    return {
                        "type": "answer",
                        "answer": "好的，已取消操作。有什么其他可以帮助您的吗？"
                    }
            
            elif clarification_type == "low_confidence":
                # User provided more details
                # Combine original query with new details
                combined_query = f"{original_query} {user_reply}"
                
                self.session_mem.write(user_id, session_id, "pending_context", None)
                return self.handle(user_id, combined_query, session_id)
            
            else:
                # Unknown clarification type, treat as new query
                logger.warning(f"Unknown clarification type: {clarification_type}")
                self.session_mem.write(user_id, session_id, "pending_context", None)
                return self.handle(user_id, user_reply, session_id)
                
        except Exception as e:
            logger.error(f"Resume failed: {e}", exc_info=True)
            return {
                "type": "answer",
                "answer": f"抱歉，恢复对话时出现错误：{str(e)}"
            }

    # =====================================================
    # === Internal Methods ===
    # =====================================================

    def _recognize_intents(self, text: str, context: List[Dict[str, str]]) -> List[Intent] | Dict:
        """
        Use LLM to extract structured intents.
        Return:
          - List[Intent] if clear
          - Dict[type='clarification', message=..., options=...] if ambiguous
        """
        logger.info(f"Recognizing intents for text: {text[:100]}")
        
        try:
            # Use IntentRecognizer to analyze the query
            result = self.intent_recognizer.recognize(text, context)
            
            # Check if result is a clarification dict
            if isinstance(result, dict) and result.get("type") == "clarification":
                logger.info("Intent recognition requires clarification")
                return result
            
            # Otherwise should be List[Intent]
            if isinstance(result, list):
                logger.info(f"Recognized {len(result)} intent(s): {[i.name for i in result]}")
                return result
            
            # Unexpected format, return error as clarification
            logger.warning(f"Unexpected intent recognition result format: {type(result)}")
            return {
                "type": "clarification",
                "message": "抱歉，我无法理解您的请求。请更清楚地描述您的需求。",
                "options": ["查询天气", "查看邮件", "搜索知识库"]
            }
            
        except Exception as e:
            logger.error(f"Intent recognition failed: {e}", exc_info=True)
            return {
                "type": "clarification",
                "message": f"处理您的请求时出现错误：{str(e)}",
                "options": ["重试", "换个问题"]
            }

    def _plan_and_execute(
        self, user_id: str, user_query: str, intents: List[Intent], context: List[Dict[str, str]]
    ) -> Dict:
        """
        Core ReAct planning & execution loop with max_rounds safety.
        """
        logger.info(f"Starting plan and execute for {len(intents)} intent(s)")
        
        steps: List[Step] = []
        used_tools: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        observations: List[str] = []
        round_count = 0

        for intent in intents:
            logger.info(f"Processing intent: {intent.name}")
            done = False
            
            while not done and round_count < self.max_rounds:
                round_count += 1
                logger.info(f"Round {round_count}/{self.max_rounds}")

                # === Step 1: Ask LLM for next action plan ===
                step = self._plan_next_step(intent, user_query, steps, observations, context)
                
                if not step:
                    # Planning failed, break
                    logger.warning("Planning failed, cannot generate next step")
                    done = True
                    break
                
                logger.info(f"Planned step - Action: {step.action}, Thought: {step.thought[:100]}")

                # === Step 2: Execute Tool if needed ===
                if step.action and step.action != "finish":
                    step.status = "running"
                    try:
                        logger.info(f"Invoking tool: {step.action} with inputs: {step.input}")
                        observation = self.tools.invoke(step.action, **step.input)
                        step.observation = observation
                        step.status = "succeeded"
                        
                        # Format observation for LLM context
                        obs_str = self._format_observation(observation)
                        observations.append(obs_str)
                        
                        used_tools.append({
                            "name": step.action,
                            "inputs": step.input,
                            "outputs": observation,
                            "status": "succeeded"
                        })
                        
                        # Extract citations if available
                        if isinstance(observation, dict):
                            if "results" in observation and isinstance(observation["results"], list):
                                for item in observation["results"]:
                                    if isinstance(item, dict) and "metadata" in item:
                                        citations.append(item["metadata"])
                        
                        logger.info(f"Tool execution succeeded: {obs_str[:100]}")
                        
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}", exc_info=True)
                        step.status = "failed"
                        step.error = str(e)
                        used_tools.append({
                            "name": step.action,
                            "inputs": step.input,
                            "outputs": {},
                            "status": "failed",
                            "error": str(e),
                        })
                        
                        # Decide whether to retry or ask user
                        observations.append(f"Tool {step.action} failed: {str(e)}")
                        
                        # For now, return clarification (can be enhanced to retry)
                        return {
                            "type": "clarification",
                            "message": f"执行工具 {step.action} 时出错：{e}\n是否要重试？",
                            "options": ["重试", "放弃"],
                        }
                elif step.action is None and intent.name == "general_qa":
                    # No tool needed - direct LLM interaction
                    step.status = "running"
                    logger.info("Processing general_qa intent - direct LLM interaction")
                    try:
                        # Use LLM directly for general questions
                        qa_response = self._direct_llm_qa(user_query, context)
                        step.observation = {"answer": qa_response}
                        step.status = "succeeded"
                        observations.append(qa_response)
                        logger.info(f"Direct LLM QA succeeded: {qa_response[:100]}")
                    except Exception as e:
                        logger.error(f"Direct LLM QA failed: {e}", exc_info=True)
                        step.status = "failed"
                        step.error = str(e)
                        observations.append(f"QA failed: {str(e)}")
                else:
                    # No action or finish action - mark as finished
                    step.status = "finished"
                    logger.info("Step marked as finished (no action or finish action)")

                steps.append(step)

                # === Step 3: Check exit condition ===
                if step.status == "finished" or step.action == "finish" or not step.decide_next:
                    done = True
                    logger.info("Intent execution completed")
                    break
                
                if step.status == "failed":
                    done = True
                    logger.warning("Intent execution failed")
                    break

            # === Max rounds reached ===
            if round_count >= self.max_rounds:
                logger.warning(f"Max rounds ({self.max_rounds}) reached")
                fail_message = (
                    "我尝试了多次规划，但未能完成任务，请重新描述您的问题。"
                )
                return {
                    "type": "answer",
                    "answer": fail_message,
                    "intents": [asdict(i) for i in intents],
                    "steps": [asdict(s) for s in steps],
                    "used_tools": used_tools,
                    "citations": citations,
                }

        # === Step 4: Summarize final result in natural language ===
        logger.info("Generating final answer from observations")
        answer = self._summarize_result(user_query, steps, observations)

        return {
            "type": "answer",
            "answer": answer,
            "intents": [asdict(i) for i in intents],
            "steps": [asdict(s) for s in steps],
            "used_tools": used_tools,
            "citations": citations,
        }
    
    def _plan_next_step(
        self, 
        intent: Intent, 
        user_query: str, 
        previous_steps: List[Step],
        observations: List[str],
        context: List[Dict[str, str]]
    ) -> Optional[Step]:
        """
        Use LLM to plan the next step based on intent and previous steps.
        """
        try:
            # Get tool descriptions
            tool_descriptions = self.tools.describe()
            
            # Build prompt for planning
            system_prompt = f"""You are a planning assistant. Based on the user's intent and previous steps, decide the next action.

Available tools:
{json.dumps(tool_descriptions, indent=2)}

You must respond with a JSON object with this structure:
{{
  "thought": "reasoning about what to do next",
  "action": "tool_name or 'finish' if done",
  "input": {{"param1": "value1"}},
  "decide_next": true/false
}}

If the task is complete, set action to "finish" and decide_next to false."""

            # Build context from previous steps
            steps_context = ""
            if previous_steps:
                steps_context = "\n\nPrevious steps:\n"
                for i, step in enumerate(previous_steps[-3:], 1):  # Last 3 steps
                    steps_context += f"{i}. Action: {step.action}, Status: {step.status}\n"
                    if step.observation:
                        obs_preview = str(step.observation)[:100]
                        steps_context += f"   Observation: {obs_preview}\n"
            
            # Build observations context
            obs_context = ""
            if observations:
                obs_context = f"\n\nObservations so far:\n" + "\n".join(observations[-3:])
            
            user_prompt = f"""User query: {user_query}
Current intent: {intent.name}
Intent slots: {json.dumps(intent.slots)}
{steps_context}{obs_context}

Plan the next step (return JSON)."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call LLM
            response = self.llm.chat(messages)
            logger.info(f"Planning LLM response: {response[:200]}")
            
            # Parse response
            return self._parse_planning_response(response, intent)
            
        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)
            
            # Fallback: use simple intent-to-action mapping
            return self._fallback_planning(intent)
    
    def _parse_planning_response(self, response: str, intent: Intent) -> Optional[Step]:
        """Parse LLM planning response into a Step object."""
        try:
            # Extract JSON from response
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            
            step = Step(
                intent=intent.name,
                thought=data.get("thought", "No thought provided"),
                action=data.get("action"),
                input=data.get("input", {}),
                observation=None,
                status="planned",
                decide_next=data.get("decide_next", True)
            )
            
            return step
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse planning response: {e}")
            return self._fallback_planning(intent)
    
    def _fallback_planning(self, intent: Intent) -> Step:
        """Simple fallback planning based on intent name."""
        action_map = {
            "get_weather": ("weather", {"location": intent.slots.get("location", "Singapore")}),
            "check_weather": ("weather", {"location": intent.slots.get("location", "Singapore")}),
            "weather_query": ("weather", {"location": intent.slots.get("location", "Singapore")}),
            "summarize_emails": ("gmail", {"count": intent.slots.get("count", 5)}),
            "read_emails": ("gmail", {"count": intent.slots.get("count", 5)}),
            "check_emails": ("gmail", {"count": intent.slots.get("count", 5)}),
            "query_knowledge": ("vdb", {"query": intent.slots.get("query", "")}),
            "search_knowledge": ("vdb", {"query": intent.slots.get("query", "")}),
            "general_qa": (None, {"query": intent.slots.get("query", "")}),  # No tool, direct LLM
        }
        
        action, inputs = action_map.get(intent.name, (None, {"query": intent.slots.get("query", "")}))
        
        return Step(
            intent=intent.name,
            thought=f"Direct mapping: {intent.name} -> {action if action else 'direct_llm'}",
            action=action,
            input=inputs,
            observation=None,
            status="planned",
            decide_next=False  # Single-step fallback
        )
    
    def _format_observation(self, observation: Any) -> str:
        """Format tool observation for LLM context."""
        if isinstance(observation, dict):
            # Format dict observations
            if "summary" in observation:
                return f"Summary: {observation['summary']}"
            elif "results" in observation:
                results = observation["results"]
                if isinstance(results, list) and results:
                    return f"Found {len(results)} results: {results[0] if results else 'None'}"
                return f"Results: {str(results)[:200]}"
            else:
                return str(observation)[:300]
        elif isinstance(observation, str):
            return observation[:300]
        else:
            return str(observation)[:300]

    # =====================================================
    # === Helper Methods ===
    # =====================================================

    def _direct_llm_qa(self, user_query: str, context: List[Dict[str, str]]) -> str:
        """
        Direct LLM interaction for general QA without tools.
        
        Args:
            user_query: User's question
            context: Conversation history
            
        Returns:
            LLM's response
        """
        logger.info(f"Direct LLM QA for: {user_query[:100]}")
        
        try:
            # Build context from conversation history
            messages = []
            
            # System prompt defining the agent's capabilities
            system_prompt = """You are a helpful and knowledgeable AI assistant. You can:
- Answer general knowledge questions
- Explain concepts and ideas
- Provide information on a wide range of topics
- Have friendly conversations
- Assist with problem-solving and brainstorming

Respond naturally and helpfully. Use the same language as the user's question (Chinese or English).
Be concise but informative. If you don't know something, say so honestly."""
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add recent conversation context (last 3 turns)
            for msg in context[-6:]:  # Last 3 user+assistant pairs
                messages.append(msg)
            
            # Add current query
            messages.append({"role": "user", "content": user_query})
            
            # Get LLM response
            response = self.llm.chat(messages)
            logger.info(f"LLM response: {response[:100]}")
            
            return response
            
        except Exception as e:
            logger.error(f"Direct LLM QA failed: {e}", exc_info=True)
            return f"抱歉，我在处理您的问题时遇到了错误：{str(e)}"
    
    def _summarize_result(
        self, user_query: str, steps: List[Step], observations: List[str]
    ) -> str:
        """
        Ask the LLM to turn tool observations into a natural-language summary.
        """
        logger.info("Summarizing results into natural language")
        
        try:
            # If no observations, return a default message
            if not observations:
                logger.warning("No observations to summarize")
                return "我暂时没有找到相关信息，请尝试更详细地描述您的需求。"
            
            # Check if this is a direct QA response (no tool used)
            if len(steps) == 1 and steps[0].action is None:
                # Already a natural language answer from direct LLM QA
                if observations and len(observations) > 0:
                    return observations[0]
            
            # Build comprehensive context from steps and observations
            context_parts = []
            context_parts.append(f"用户问题：{user_query}")
            context_parts.append(f"\n执行了 {len(steps)} 个步骤，获得以下信息：")
            
            # Focus on observations, not the technical steps
            for i, obs in enumerate(observations, 1):
                context_parts.append(f"\n信息 {i}: {obs}")
            
            context_str = "\n".join(context_parts)
            
            # Create prompt for natural language summarization
            system_prompt = """You are a helpful AI assistant. Convert the information gathered from various sources into a natural, conversational response.

Requirements:
1. Answer the user's question directly - don't repeat their question
2. Use clear, natural language - avoid technical jargon
3. Combine multiple pieces of information into a cohesive answer
4. Match the language of the user's question (Chinese or English)
5. Be friendly and professional
6. If the information is empty or insufficient, suggest alternatives

DO NOT output raw data or JSON. Always provide a human-friendly response."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_str}
            ]
            
            answer = self.llm.chat(messages)
            
            # Check if LLM is in mock mode
            if answer.startswith("(mocked-llm)") or "mocked" in answer.lower():
                logger.warning("LLM in mock mode, using fallback formatting")
                # Use better fallback formatting
                return self._format_fallback_answer(user_query, observations)
            
            logger.info(f"Generated answer: {answer[:100]}")
            return answer
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}", exc_info=True)
            return self._format_fallback_answer(user_query, observations)
    
    def _format_fallback_answer(self, user_query: str, observations: List[str]) -> str:
        """
        Format a fallback answer when LLM summarization fails or is in mock mode.
        """
        if not observations:
            return "我暂时没有找到相关信息。"
        
        # Detect language
        is_chinese = any('\u4e00' <= c <= '\u9fff' for c in user_query)
        
        if len(observations) == 1:
            return observations[0]
        
        # Multiple observations - format as list
        if is_chinese:
            answer = "根据查询结果：\n\n"
            for i, obs in enumerate(observations, 1):
                answer += f"• {obs}\n"
        else:
            answer = "Based on the query results:\n\n"
            for i, obs in enumerate(observations, 1):
                answer += f"• {obs}\n"
        
        return answer.strip()
