"""tool argument validation helpers"""
from typing import Dict
from backend.domain.enums import ToolName

LANGUAGE_TOOLS = frozenset({
    ToolName.RESOLVE_MEDICATION_ID.value,
    ToolName.GET_MEDICATION_INFO.value,
    ToolName.SEARCH_BY_INGREDIENT.value,
    ToolName.FIND_NEAREST_PHARMACY.value,
    ToolName.GET_HANDLING_WARNINGS.value,
    ToolName.GET_USER_PRESCRIPTIONS.value
})


def is_language_tool(name: str) -> bool:
    """return True if tool supports language parameter"""
    return name in LANGUAGE_TOOLS


def has_required_arguments(name: str, args: Dict[str, str]) -> bool:
    """validate tool arguments at a minimal level"""
    if name == ToolName.GET_MEDICATION_INFO.value:
        return bool(args.get("query"))
    if name == ToolName.RESOLVE_MEDICATION_ID.value:
        return bool(args.get("name"))
    if name == ToolName.SEARCH_BY_INGREDIENT.value:
        return bool(args.get("ingredient"))
    if name == ToolName.FIND_NEAREST_PHARMACY.value:
        return bool(args.get("zip_code") or args.get("city"))
    if name == ToolName.CHECK_STOCK.value:
        return bool(args.get("med_id"))
    if name == ToolName.GET_HANDLING_WARNINGS.value:
        return bool(args.get("med_id"))
    if name == ToolName.GET_USER_PRESCRIPTIONS.value:
        return True
    return bool(args)
