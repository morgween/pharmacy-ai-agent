"""tool-related user-facing messages"""
from typing import Optional

MISSING_PARAM_MESSAGES = {
    "find_nearest_pharmacy": "Please specify a city or zip code to find nearby pharmacies.",
    "get_medication_info": "Please specify which medication you'd like information about.",
    "check_stock": "Please specify which medication to check stock for.",
    "search_by_ingredient": "Please specify an ingredient to search for.",
    "resolve_medication_id": "Please provide a medication name.",
    "get_handling_warnings": "Please specify which medication you need handling warnings for."
}


def get_missing_param_message(tool_name: str) -> Optional[str]:
    """get a missing parameter message for a tool name"""
    return MISSING_PARAM_MESSAGES.get(tool_name)
