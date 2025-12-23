"""enum definitions for pharmacy ai agent"""
from enum import Enum


class Language(str, Enum):
    """supported language codes"""
    EN = "en"
    HE = "he"
    RU = "ru"
    AR = "ar"


class PrescriptionStatus(str, Enum):
    """allowed prescription statuses"""
    PENDING = "pending"
    READY = "ready"
    EXPIRED = "expired"


class ToolName(str, Enum):
    """tool names supported by the agent"""
    RESOLVE_MEDICATION_ID = "resolve_medication_id"
    GET_MEDICATION_INFO = "get_medication_info"
    CHECK_STOCK = "check_stock"
    SEARCH_BY_INGREDIENT = "search_by_ingredient"
    GET_USER_PRESCRIPTIONS = "get_user_prescriptions"
    GET_HANDLING_WARNINGS = "get_handling_warnings"
    FIND_NEAREST_PHARMACY = "find_nearest_pharmacy"
