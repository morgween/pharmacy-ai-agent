"""medication tool handlers"""
import logging
from typing import Dict, Any

from backend.domain.messages import Messages
from backend.utils.response import tool_error_handler

logger = logging.getLogger(__name__)


class MedicationTools:
    """medication lookup tools"""

    def __init__(self, medications_api: Any, format_ambiguous_response) -> None:
        self._medications_api = medications_api
        self._format_ambiguous_response = format_ambiguous_response

    @tool_error_handler(error_key="search_failed", message_category="MEDICATION")
    async def search_by_ingredient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        tool: search_by_ingredient
        purpose: find medications by active ingredient in the requested language.

        inputs:
            ingredient (str, required): active ingredient to search for.
            lang (str, optional): language code, defaults to "en".

        output schema:
            success (bool)
            matches (int) when success is true
            medications (list[dict]) when success is true
                - id (str)
                - name (str)
                - active_ingredient (str)
                - dosage (str)
                - prescription_required (bool)
                - price_usd (float)
                - category (str)
            message (str, optional) on no results or errors
            error (str, optional) on validation or failure

        error handling:
            - missing ingredient returns success false with error string and localized message.
            - unexpected exceptions are handled by tool_error_handler -> error "search_failed".

        fallback behavior:
            - no matches returns success true with empty list and localized message.
            - localized fields fall back to english if requested language is missing.
        """
        ingredient = args.get('ingredient')
        lang = args.get('lang', 'en')

        if not ingredient:
            logger.warning("search_by_ingredient called without ingredient parameter")
            return {
                "success": False,
                "error": "missing required parameter: ingredient",
                "message": Messages.get("MEDICATION", "missing_ingredient", lang)
            }

        results = await self._medications_api.search_by_ingredient(
            ingredient=ingredient,
            language=lang
        )

        if not results:
            logger.info(f"no medications found for ingredient: {ingredient}")
            return {
                "success": True,
                "matches": 0,
                "medications": [],
                "message": Messages.get(
                    "MEDICATION",
                    "no_results",
                    lang,
                    ingredient=ingredient
                )
            }

        # defensive dict access with fallback to english
        medications = []
        for med in results:
            try:
                medications.append({
                    "id": med.get('id', 'unknown'),
                    "name": med.get('names', {}).get(lang, med.get('names', {}).get('en', 'Unknown')),
                    "active_ingredient": med.get('active_ingredient', {}).get(lang, med.get('active_ingredient', {}).get('en', 'Unknown')),
                    "dosage": med.get('dosage', 'Not specified'),
                    "prescription_required": med.get('prescription_required', False),
                    "price_usd": med.get('price_usd', 0.0),
                    "category": med.get('category', {}).get(lang, med.get('category', {}).get('en', 'General'))
                })
            except Exception as e:
                logger.warning(f"error processing medication {med.get('id', 'unknown')}: {e}")
                # skip this medication but continue with others
                continue

        logger.info(f"found {len(medications)} medications for ingredient: {ingredient}")
        return {
            "success": True,
            "matches": len(medications),
            "medications": medications
        }

    @tool_error_handler(error_key="resolve_failed", message_category="MEDICATION")
    async def resolve_medication_id(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        tool: resolve_medication_id
        purpose: resolve a medication name to its internal ID.

        inputs:
            name (str, required): medication name to resolve.
            lang (str, optional): language code, defaults to "en".

        output schema:
            success (bool)
            id (str) on success
            name (str) on success
            message (str, optional) on not found
            error (str, optional) on validation or failure
            candidates (list[str], optional) on ambiguous matches

        error handling:
            - missing name returns success false with error string and localized message.
            - unexpected exceptions are handled by tool_error_handler -> error "resolve_failed".

        fallback behavior:
            - ambiguous match returns an "ambiguous_match" response with candidates.
            - name field falls back to english when localized name is missing.
        """
        name = args.get('name')
        lang = args.get('lang', 'en')

        if not name:
            logger.warning("resolve_medication_id called without name parameter")
            return {
                "success": False,
                "error": "missing required parameter: name",
                "message": Messages.get("MEDICATION", "missing_name", lang)
            }

        med = await self._medications_api.get_medication_by_name(
            name=name,
            language=lang
        )

        if med and med.get("_ambiguous"):
            logger.info(f"ambiguous medication match for '{name}' (language: {lang})")
            return self._format_ambiguous_response(med.get("candidates", []), lang)

        if med:
            logger.info(f"resolved medication '{name}' to ID: {med.get('id')}")
            return {
                "success": True,
                "id": med.get('id', 'unknown'),
                "name": med.get('names', {}).get(lang, med.get('names', {}).get('en', name))
            }

        logger.info(f"medication not found: '{name}' (language: {lang})")
        return {
            "success": False,
            "message": Messages.get("MEDICATION", "resolve_not_found", lang, name=name)
        }

    @tool_error_handler(
        error_key="info_retrieval_failed",
        message_category="MEDICATION",
        message_key="info_failed"
    )
    async def get_medication_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        tool: get_medication_info
        purpose: fetch full, label-based medication information by name or ID.

        inputs:
            query (str, required): medication name or id.
            lang (str, optional): language code, defaults to "en".

        output schema:
            success (bool)
            medication (dict) on success
                - id (str)
                - name (str)
                - active_ingredient (str)
                - dosage (str)
                - prescription_required (bool)
                - usage_instructions (str)
                - warnings (str)
                - category (str)
                - price_usd (float)
            message (str, optional) on not found
            error (str, optional) on validation or failure
            candidates (list[str], optional) on ambiguous matches

        error handling:
            - missing query returns success false with error string and localized message.
            - unexpected exceptions are handled by tool_error_handler -> error "info_retrieval_failed".

        fallback behavior:
            - ambiguous match returns an "ambiguous_match" response with candidates.
            - localized fields fall back to english when missing.
        """
        query = args.get('query')
        lang = args.get('lang', 'en')

        if not query:
            logger.warning("get_medication_info called without query parameter")
            return {
                "success": False,
                "error": "missing required parameter: query",
                "message": Messages.get("MEDICATION", "missing_query", lang)
            }

        # try to find by id first, then by name
        med = None
        if hasattr(self._medications_api, "get_medication_by_id"):
            med = await self._medications_api.get_medication_by_id(query)

        if not med:
            med = await self._medications_api.get_medication_by_name(
                name=query,
                language=lang
            )

        if med and med.get("_ambiguous"):
            logger.info(f"ambiguous medication match for '{query}' (language: {lang})")
            return self._format_ambiguous_response(med.get("candidates", []), lang)

        if not med:
            logger.info(f"medication not found: '{query}' (language: {lang})")
            return {
                "success": False,
                "message": Messages.get("MEDICATION", "info_not_found", lang, query=query)
            }

        # defensive dict access with fallback to english
        logger.info(f"found medication info for: {query} (ID: {med.get('id')})")
        return {
            "success": True,
            "medication": {
                "id": med.get('id', 'unknown'),
                "name": med.get('names', {}).get(lang, med.get('names', {}).get('en', 'Unknown')),
                "active_ingredient": med.get('active_ingredient', {}).get(lang, med.get('active_ingredient', {}).get('en', 'Unknown')),
                "dosage": med.get('dosage', 'Not specified'),
                "prescription_required": med.get('prescription_required', False),
                "usage_instructions": med.get('usage_instructions', {}).get(lang, med.get('usage_instructions', {}).get('en', 'Consult a pharmacist')),
                "warnings": med.get('warnings', {}).get(lang, med.get('warnings', {}).get('en', 'Consult a pharmacist')),
                "category": med.get('category', {}).get(lang, med.get('category', {}).get('en', 'General')),
                "price_usd": med.get('price_usd', 0.0)
            }
        }
