"""stream processing helpers for chat completions"""
import asyncio
import json
from typing import Any, AsyncIterator, List, Optional


class StreamProcessor:
    """process streamed chat completion chunks into SSE payloads"""

    def __init__(
        self,
        *,
        safety_guard: Any,
        detected_language: str,
        tool_call_accumulator: Any,
        tool_calls_made: List[str],
        effective_user_id: Optional[str],
        user_db: Any,
        assistant_content: str,
        total_tokens: int
    ) -> None:
        self._safety_guard = safety_guard
        self._detected_language = detected_language
        self._tool_call_accumulator = tool_call_accumulator
        self._tool_calls_made = tool_calls_made
        self._effective_user_id = effective_user_id
        self._user_db = user_db

        self.assistant_content = assistant_content
        self.step_assistant_content = ""
        self.buffered_text = ""
        self.tool_calls_detected = False
        self.safety_blocked = False
        self.total_tokens = total_tokens

    async def iter_chunks(self, response: Any) -> AsyncIterator[str]:
        """yield SSE payloads while updating internal state"""
        async for chunk in response:
            chunk_dict = chunk.model_dump()

            delta = chunk_dict.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                self.step_assistant_content += delta["content"]
                self.assistant_content += delta["content"]
                if not self.tool_calls_detected:
                    self.buffered_text += delta["content"]
                violation_reason = self._safety_guard.check_text(self.assistant_content)
                if violation_reason:
                    self.assistant_content = self._safety_guard.refusal_message(
                        violation_reason,
                        self._detected_language
                    )
                    safety_chunk = {
                        "choices": [
                            {
                                "delta": {"content": self.assistant_content}
                            }
                        ]
                    }
                    yield f"data: {json.dumps(safety_chunk)}\n\n"
                    self.safety_blocked = True
                    break

            if delta.get("tool_calls"):
                self.tool_calls_detected = True
                tool_names = self._tool_call_accumulator.add_delta(delta["tool_calls"])
                for tool_name in tool_names:
                    if tool_name and tool_name not in self._tool_calls_made:
                        self._tool_calls_made.append(tool_name)
                        if self._effective_user_id:
                            await asyncio.to_thread(
                                self._user_db.track_tool_call,
                                self._effective_user_id,
                                tool_name
                            )

            if self.tool_calls_detected:
                if "content" in delta:
                    delta.pop("content", None)
                    chunk_dict["choices"][0]["delta"] = delta
                yield f"data: {json.dumps(chunk_dict)}\n\n"
            elif delta.get("content") is None:
                yield f"data: {json.dumps(chunk_dict)}\n\n"

            if chunk_dict.get("usage"):
                self.total_tokens = chunk_dict["usage"].get("total_tokens", 0)
