"""handling and warnings tool handlers"""
import logging
from typing import Dict, Any

from backend.i18n.messages import Messages
from backend.utils.response import tool_error_handler

logger = logging.getLogger(__name__)


class HandlingTools:
    """medication handling tools"""

    def __init__(self, medications_api: Any) -> None:
        self._medications_api = medications_api

    @tool_error_handler(error_key="retrieval_failed", message_category="HANDLING")
    async def get_handling_warnings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        tool: get_handling_warnings
        purpose: return label-based handling guidance and warnings for a medication.

        inputs:
            med_id (str, required): medication id to look up.
            lang (str, optional): language code, defaults to "en".

        output schema:
            success (bool)
            med_id (str)
            medication_name (str)
            handling_instructions (list[str])
            label_warnings (str)
            message (str)
            error (str, optional) on failure

        error handling:
            - missing med_id returns success false with error "missing_parameter".
            - not found returns success false with error "not_found".
            - unexpected exceptions are handled by tool_error_handler -> error "retrieval_failed".

        fallback behavior:
            - localized fields fall back to english when missing.
            - returns only label-based content; no personalized advice.
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
