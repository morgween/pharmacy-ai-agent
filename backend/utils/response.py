"""tool response helpers"""
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional

from backend.i18n.messages import Messages

logger = logging.getLogger(__name__)


def tool_error_handler(
    error_key: str,
    message_category: str,
    message_key: Optional[str] = None
) -> Callable[[Callable[..., Awaitable[Dict[str, Any]]]], Callable[..., Awaitable[Dict[str, Any]]]]:
    """decorator for consistent tool error handling"""
    def decorator(func: Callable[..., Awaitable[Dict[str, Any]]]):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                lang = "en"
                payload = None
                if len(args) > 1 and isinstance(args[1], dict):
                    payload = args[1]
                elif isinstance(kwargs.get("args"), dict):
                    payload = kwargs.get("args")
                if payload:
                    lang = payload.get("lang", "en")

                message_id = message_key or error_key
                message = Messages.get(message_category, message_id, lang)
                logger.error("error in %s: %s", func.__name__, exc, exc_info=True)
                return {
                    "success": False,
                    "error": error_key,
                    "message": message
                }
        return wrapper
    return decorator
