"""tool execution runner"""
import json
import logging
from typing import Any, Dict, List, Tuple

from backend.tool_framework.inference import infer_tool_arguments
from backend.tool_framework.validators import is_language_tool, has_required_arguments
from backend.tool_framework.messages import get_missing_param_message

logger = logging.getLogger(__name__)


class ToolRunner:
    """execute tool calls and build tool messages"""

    def __init__(
        self,
        *,
        service: Any,
        last_user_message: str,
        detected_language: str,
        effective_user_id: str | None
    ) -> None:
        self._service = service
        self._last_user_message = last_user_message
        self._detected_language = detected_language
        self._effective_user_id = effective_user_id
        self.tool_messages: List[Dict[str, str]] = []

    def _parse_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> Tuple[List[Tuple[Dict[str, Any], str, Dict[str, Any]]], List[Tuple[Dict[str, Any], str, Dict[str, Any]]]]:
        parsed_tool_calls: List[Tuple[Dict[str, Any], str, Dict[str, Any]]] = []
        empty_tool_calls: List[Tuple[Dict[str, Any], str, Dict[str, Any]]] = []

        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name")
            if not function_name:
                continue

            args_str = tool_call.get("function", {}).get("arguments", "")
            if not args_str:
                logger.warning(
                    f"tool call {function_name} received empty arguments"
                )
            try:
                arguments = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                logger.warning(
                    f"failed to parse tool arguments for {function_name}: {args_str}"
                )
                arguments = {}

            if not arguments:
                logger.warning(
                    f"tool call {function_name} has empty parsed arguments"
                )
                inferred_args = infer_tool_arguments(
                    function_name,
                    self._last_user_message,
                    self._detected_language,
                    self._service
                )
                if inferred_args:
                    logger.info(
                        f"inferred arguments for {function_name}: {inferred_args}"
                    )
                    arguments.update(inferred_args)

            if function_name == "get_user_prescriptions" and "user_id" not in arguments:
                if self._effective_user_id:
                    arguments["user_id"] = self._effective_user_id

            if is_language_tool(function_name) and has_required_arguments(function_name, arguments):
                arguments["lang"] = self._detected_language

            if has_required_arguments(function_name, arguments):
                parsed_tool_calls.append((tool_call, function_name, arguments))
            else:
                empty_tool_calls.append((tool_call, function_name, arguments))

        return parsed_tool_calls, empty_tool_calls

    async def run(self, tool_calls: List[Dict[str, Any]]):
        """run tool calls and yield tool execution SSE payloads"""
        parsed_tool_calls, empty_tool_calls = self._parse_tool_calls(tool_calls)
        all_tool_calls = parsed_tool_calls + empty_tool_calls

        for tool_call, function_name, arguments in all_tool_calls:
            if arguments:
                tool_execution_chunk = {
                    "tool_execution": {
                        "id": tool_call["id"],
                        "name": function_name,
                        "arguments": arguments
                    }
                }
                yield f"data: {json.dumps(tool_execution_chunk)}\n\n"
                result = await self._service.execute_function_call(function_name, arguments)
            else:
                logger.warning(f"tool {function_name} called with no arguments, returning error")
                missing_message = get_missing_param_message(function_name)
                result = {
                    "success": False,
                    "error": "missing_parameters",
                    "message": missing_message or "Please provide the required information to complete this request."
                }

            logger.info(
                f"tool {function_name} result summary: "
                f"success={result.get('success')} keys={list(result.keys())}"
            )
            self.tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result)
                }
            )
