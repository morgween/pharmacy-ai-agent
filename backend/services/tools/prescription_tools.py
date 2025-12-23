"""prescription tool handlers"""
import asyncio
import logging
from typing import Dict, Any

from backend.i18n.messages import Messages
from backend.utils.response import tool_error_handler

logger = logging.getLogger(__name__)


class PrescriptionTools:
    """user prescription tools"""

    def __init__(self, user_db: Any, medications_api: Any) -> None:
        self._user_db = user_db
        self._medications_api = medications_api

    @tool_error_handler(
        error_key="retrieval_failed",
        message_category="PRESCRIPTION",
        message_key="failed"
    )
    async def get_user_prescriptions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        tool: get_user_prescriptions
        purpose: return a user's prescriptions, optionally filtered to active only.

        inputs:
            user_id (str, required): authenticated user id.
            active_only (bool, optional): defaults to true.
            lang (str, optional): language code, defaults to "en".

        output schema:
            success (bool)
            count (int)
            active_only (bool)
            prescriptions (list[dict])
                - prescription_id (str)
                - patient_id (str)
                - med_id (str)
                - med_name (str, optional)
                - prescriber_name (str)
                - quantity (int)
                - pickup_location (str)
                - status (str)
                - notes (str or null)
                - created_at (str or null)
                - updated_at (str or null)
                - ready_at (str or null)
                - picked_up_at (str or null)
            message (str)
            error (str, optional) on failure

        error handling:
            - missing user_id returns success false with error "missing_user".
            - unexpected exceptions are handled by tool_error_handler -> error "retrieval_failed".

        fallback behavior:
            - no prescriptions returns success true with count 0 and localized message.
            - med_name uses english if localized name is missing.
        """
        user_id = args.get("user_id")
        active_only = args.get("active_only", True)
        lang = args.get("lang", "en")

        if not user_id:
            return {
                "success": False,
                "error": "missing_user",
                "message": Messages.get("PRESCRIPTION", "missing_user", lang)
            }

        prescriptions = await asyncio.to_thread(
            self._user_db.get_user_prescriptions,
            user_id,
            active_only
        )

        if not prescriptions:
            message_key = "none_active" if active_only else "none_all"
            return {
                "success": True,
                "count": 0,
                "active_only": active_only,
                "prescriptions": [],
                "message": Messages.get("PRESCRIPTION", message_key, lang)
            }

        enriched = []
        for prescription in prescriptions:
            med_id = prescription.get("med_id")
            med_name = None
            if med_id and hasattr(self._medications_api, "get_medication_by_id"):
                med = await self._medications_api.get_medication_by_id(med_id)
                if med:
                    med_name = med.get("names", {}).get(
                        lang,
                        med.get("names", {}).get("en")
                    )
            enriched.append({
                **prescription,
                "med_name": med_name
            })

        return {
            "success": True,
            "count": len(enriched),
            "active_only": active_only,
            "prescriptions": enriched,
            "message": Messages.get("PRESCRIPTION", "found", lang, count=len(enriched))
        }
