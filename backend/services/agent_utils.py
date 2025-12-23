"""shared helper utilities for agent services"""
import json
import logging
import os
from typing import Any, Dict, List

from backend.i18n.messages import Messages

logger = logging.getLogger(__name__)


def load_static_json(filename: str) -> Any:
    """
    load static json file from data directory

    args:
        filename: name of the json file in data directory

    returns:
        parsed json data
    """
    try:
        filepath = os.path.join(os.path.dirname(__file__), "..", "..", "data", filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"loaded static data: {filename}")
        return data
    except Exception as e:
        logger.error(f"failed to load static json {filename}: {e}")
        return [] if filename.endswith("locations.json") else {}


def format_ambiguous_response(
    candidates: List[Dict[str, Any]],
    lang: str
) -> Dict[str, Any]:
    """Build a clarification response when multiple meds match within threshold."""
    names = [candidate.get("name") for candidate in candidates if candidate.get("name")]
    options = names[:3]
    options_text = ", ".join(options) if options else ""

    message = Messages.get("GENERAL", "ambiguous_match", lang, options=options_text)

    return {
        "success": False,
        "error": "ambiguous_match",
        "message": message,
        "candidates": options
    }
