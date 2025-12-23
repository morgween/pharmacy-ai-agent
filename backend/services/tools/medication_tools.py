"""medication tool handlers"""
import logging
from typing import Dict, Any

from backend.i18n.messages import Messages

logger = logging.getLogger(__name__)


class MedicationTools:
    """medication lookup tools"""

    def __init__(self, medications_api: Any, format_ambiguous_response) -> None:
        self._medications_api = medications_api
        self._format_ambiguous_response = format_ambiguous_response

    async def search_by_ingredient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute search_by_ingredient function with error handling

        args:
            args: dictionary containing ingredient and lang parameters

        returns:
            search results with matching medications
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

        try:
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

        except Exception as e:
            logger.error(f"error searching by ingredient '{ingredient}': {e}", exc_info=True)
            return {
                "success": False,
                "error": "search_failed",
                "message": Messages.get("MEDICATION", "search_failed", lang)
            }



    async def resolve_medication_id(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute resolve_medication_id function with error handling

        args:
            args: dictionary containing name and lang parameters

        returns:
            medication id if found
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

        try:
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

        except Exception as e:
            logger.error(f"error resolving medication name '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": "resolve_failed",
                "message": Messages.get("MEDICATION", "resolve_failed", lang)
            }



    async def get_medication_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute get_medication_info function with error handling

        args:
            args: dictionary containing query and optional lang parameters

        returns:
            full medication information
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

        try:
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

        except Exception as e:
            logger.error(f"error getting medication info for '{query}': {e}", exc_info=True)
            return {
                "success": False,
                "error": "info_retrieval_failed",
                "message": Messages.get("MEDICATION", "info_failed", lang)
            }
