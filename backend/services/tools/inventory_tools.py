"""inventory tool handlers"""
import json
import logging
from typing import Dict, Any

import httpx

from backend.config import settings
from backend.i18n.messages import Messages

logger = logging.getLogger(__name__)


class InventoryTools:
    """inventory tools"""

    def __init__(self) -> None:
        pass

    async def check_stock(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute check_stock function by calling inventory api with comprehensive error handling

        args:
            args: dictionary containing med_id parameter

        returns:
            boolean availability status (not exact quantity)
        """
        med_id = args.get('med_id')
        lang = args.get('lang', 'en')

        if not med_id:
            logger.warning("check_stock called without med_id parameter")
            return {
                "success": False,
                "error": "missing required parameter: med_id",
                "message": Messages.get("INVENTORY", "missing_med_id", lang)
            }

        try:
            url = f"{settings.inventory_service_url}/check_stock/{med_id}"
            logger.debug(f"checking stock for {med_id} at {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=settings.openai_timeout)
                response.raise_for_status()
                data = response.json()

                logger.info(f"stock check for {med_id}: {data.get('in_stock', False)}")
                return {
                    "success": True,
                    "id": data.get('id', med_id),
                    "in_stock": data.get('in_stock', False)
                }

        except httpx.TimeoutException:
            logger.error(f"timeout checking stock for {med_id}")
            return {
                "success": False,
                "error": "timeout",
                "message": Messages.get("INVENTORY", "timeout", lang)
            }
        except httpx.ConnectError:
            logger.error(f"connection error to inventory service: {settings.inventory_service_url}")
            return {
                "success": False,
                "error": "service_unavailable",
                "message": Messages.get("INVENTORY", "service_unavailable", lang)
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"medication {med_id} not found in inventory")
                return {
                    "success": False,
                    "error": "not_found",
                    "message": Messages.get("INVENTORY", "not_found", lang, med_id=med_id)
                }
            logger.error(f"http error checking stock for {med_id}: {e.response.status_code}")
            return {
                "success": False,
                "error": "http_error",
                "message": Messages.get("INVENTORY", "http_error", lang)
            }
        except json.JSONDecodeError:
            logger.error(f"invalid json response from inventory service for {med_id}")
            return {
                "success": False,
                "error": "invalid_response",
                "message": Messages.get("INVENTORY", "invalid_response", lang)
            }
        except Exception as e:
            logger.error(f"unexpected error checking stock for {med_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "unknown",
                "message": Messages.get("INVENTORY", "unknown", lang)
            }
