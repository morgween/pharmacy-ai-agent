"""shared constants for pharmacy ai agent"""
from backend.domain.enums import Language, PrescriptionStatus

SUPPORTED_LANGUAGES = tuple(lang.value for lang in Language)
RTL_LANGUAGES = (Language.HE.value, Language.AR.value)

PRESCRIPTION_ACTIVE_STATUSES = (
    PrescriptionStatus.PENDING.value,
    PrescriptionStatus.READY.value
)
PRESCRIPTION_STATUSES = tuple(status.value for status in PrescriptionStatus)

ALLOWED_TOOL_SCHEMAS = (
    "resolve_medication_id.json",
    "get_medication_info.json",
    "check_stock.json",
    "search_by_ingredient.json",
    "get_user_prescriptions.json",
    "get_handling_warnings.json",
    "find_nearest_pharmacy.json"
)
