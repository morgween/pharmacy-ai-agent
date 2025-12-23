"""handling and warnings tool handlers"""
import logging
from typing import Dict, Any

from backend.i18n.messages import Messages

logger = logging.getLogger(__name__)


class HandlingTools:
    """medication handling tools"""

    def __init__(self, medications_api: Any) -> None:
        self._medications_api = medications_api

    async def get_handling_warnings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute get_handling_warnings function with error handling

        args:
            args: dictionary containing med_id and optional lang parameters

        returns:
            safe handling instructions and warnings from medication labels
        """
        med_id = args.get('med_id')
        lang = args.get('lang', 'en')

        if not med_id:
            logger.warning("get_handling_warnings called without med_id")
            return {
                "success": False,
                "error": "missing_parameter",
                "message": Messages.get("HANDLING", "missing_med_id", lang)
            }

        try:
            # find medication in knowledge base
            med = None
            if hasattr(self._medications_api, "get_medication_by_id"):
                med = await self._medications_api.get_medication_by_id(med_id)
            if not med and hasattr(self._medications_api, "medications"):
                for m in self._medications_api.medications:
                    if m.get('id') == med_id:
                        med = m
                        break

            if not med:
                logger.info(f"medication not found for handling warnings: {med_id}")
                return {
                    "success": False,
                    "error": "not_found",
                    "message": Messages.get("HANDLING", "not_found", lang, med_id=med_id)
                }

            # extract handling and warning information from label data
            warnings = med.get('warnings', {}).get(lang, med.get('warnings', {}).get('en', ''))

            # construct safe handling instructions (factual, label-based only)
            handling_instructions = []

            # storage information
            handling_instructions.append(Messages.get("HANDLING", "storage", lang))

            # child safety
            handling_instructions.append(Messages.get("HANDLING", "child_safety", lang))

            # general safety
            if med.get('prescription_required'):
                handling_instructions.append(Messages.get("HANDLING", "prescription", lang))

            logger.info(f"retrieved handling warnings for {med_id}")

            return {
                "success": True,
                "med_id": med_id,
                "medication_name": med.get('names', {}).get(lang, med.get('names', {}).get('en', 'Unknown')),
                "handling_instructions": handling_instructions,
                "label_warnings": warnings,
                "message": Messages.get("HANDLING", "message", lang)
            }

        except Exception as e:
            logger.error(f"error getting handling warnings for {med_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "retrieval_failed",
                "message": Messages.get("HANDLING", "retrieval_failed", lang)
            }
