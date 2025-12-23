"""tool call parsing and accumulation helpers"""
from typing import Dict, Any, List


class ToolCallAccumulator:
    """accumulate streamed tool call deltas into complete tool calls"""

    def __init__(self) -> None:
        self._accumulator: Dict[str, Dict[str, Any]] = {}
        self._index_map: Dict[int, str] = {}

    def add_delta(self, tool_calls: List[Dict[str, Any]]) -> List[str]:
        """
        add tool call delta chunks and return any tool names discovered

        args:
            tool_calls: list of tool call delta payloads

        returns:
            list of tool names detected in this delta
        """
        names: List[str] = []
        for tc in tool_calls:
            tc_index = tc.get("index", 0)
            call_id = tc.get("id")

            if call_id:
                self._index_map[tc_index] = call_id
            else:
                call_id = self._index_map.get(tc_index)
                if not call_id:
                    continue

            entry = self._accumulator.setdefault(
                call_id,
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": None, "arguments": ""}
                }
            )

            function_data = tc.get("function", {})
            tool_name = function_data.get("name")
            if tool_name:
                entry["function"]["name"] = tool_name
                names.append(tool_name)

            arguments = function_data.get("arguments")
            if arguments:
                entry["function"]["arguments"] += arguments

        return names

    def build(self) -> List[Dict[str, Any]]:
        """return accumulated tool calls as a list"""
        return list(self._accumulator.values())

    def reset(self) -> None:
        """clear accumulated tool calls and index map"""
        self._accumulator.clear()
        self._index_map.clear()
