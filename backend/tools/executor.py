"""tool executor for pharmacy ai agent"""
import logging
from typing import Dict, Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class ToolExecutor:
    """dispatch tool calls to handler implementations with error handling"""

    def __init__(self, handlers: Any):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
            "search_by_ingredient": handlers.search_by_ingredient,
            "resolve_medication_id": handlers.resolve_medication_id,
            "get_medication_info": handlers.get_medication_info,
            "check_stock": handlers.check_stock,
            "find_nearest_pharmacy": handlers.find_nearest_pharmacy,
            "get_user_prescriptions": handlers.get_user_prescriptions,
            "get_handling_warnings": handlers.get_handling_warnings,
        }

    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute a function call and return results with error handling

        args:
            function_name: name of the function to execute
            arguments: function arguments as dict

        returns:
            function execution result dict
        """
        logger.info(f"executing function call: {function_name} with args: {arguments}")

        handler = self._handlers.get(function_name)
        if not handler:
            logger.error(f"unknown function called: {function_name}")
            return {
                "success": False,
                "error": f"unknown function: {function_name}",
                "message": "I encountered an internal error. Please try again or contact support."
            }

        try:
            result = await handler(arguments)
            logger.debug(f"function {function_name} result: {result}")
            return result
        except Exception as e:
            logger.error(f"unexpected error executing {function_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "internal_error",
                "message": "I encountered an unexpected error while processing your request. Please try again."
            }
