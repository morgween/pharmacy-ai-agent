"""prescription tool handlers"""
import asyncio
import logging
from typing import Dict, Any

from backend.i18n.messages import Messages

logger = logging.getLogger(__name__)


class PrescriptionTools:
    """user prescription tools"""

    def __init__(self, user_db: Any, medications_api: Any) -> None:
        self._user_db = user_db
        self._medications_api = medications_api

    async def get_user_prescriptions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        list prescriptions for a user

        args:
            args: dictionary containing user_id, optional active_only, optional lang

        returns:
            prescriptions for the user
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

        try:
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
        except Exception as e:
            logger.error(f"error getting prescriptions for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "retrieval_failed",
                "message": Messages.get("PRESCRIPTION", "failed", lang)
            }
