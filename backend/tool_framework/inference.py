"""tool argument inference helpers"""
import re
from typing import Dict, List, Any

from backend.constants import SUPPORTED_LANGUAGES
from backend.data_sources.base import normalize_text, levenshtein_distance


def collect_medications(service: Any, language: str) -> List[Dict[str, str]]:
    """Collect medication names and ingredients for matching."""
    medications = []
    if hasattr(service.medications_api, "medications"):
        for med in service.medications_api.medications:
            name = med.get("names", {}).get(language)
            active = med.get("active_ingredient", {}).get(language)
            if name:
                medications.append({"id": med.get("id"), "name": name, "active": active or ""})
    else:
        for med in service.medications_api.get_all_medications(language):
            name = med.get("name")
            active = med.get("active_ingredient")
            if name:
                medications.append({"id": med.get("id"), "name": name, "active": active or ""})
    return medications


def infer_tool_arguments(
    function_name: str,
    text: str,
    detected_language: str,
    service: Any
) -> Dict[str, str]:
    """Infer missing tool arguments from the last user message."""
    if not text:
        return {}

    text_fold = text.casefold()
    text_lower = text.lower()

    # handle find_nearest_pharmacy - extract city or zip code
    if function_name == "find_nearest_pharmacy":
        pharmacy_locations = getattr(service, '_pharmacy_locations', [])
        known_cities = set()
        for location in pharmacy_locations:
            city = location.get('city', '')
            if city:
                known_cities.add(city.lower())

        for city in known_cities:
            if city in text_lower:
                for location in pharmacy_locations:
                    if location.get('city', '').lower() == city:
                        return {"city": location['city'], "lang": detected_language}

        zip_match = re.search(r'\b(\d{5,7})\b', text)
        if zip_match:
            return {"zip_code": zip_match.group(1), "lang": detected_language}

        return {}

    tokens = re.findall(r"[A-Za-z\u0590-\u05FF\u0400-\u04FF\u0600-\u06FF]+", text)
    languages = [detected_language] + [lang for lang in SUPPORTED_LANGUAGES if lang != detected_language]
    best_match = None

    for lang in languages:
        for med in collect_medications(service, lang):
            name = med.get("name", "")
            active = med.get("active", "")
            if name and name.casefold() in text_fold:
                best_match = {"id": med.get("id"), "name": name, "active": active, "lang": lang}
                break
            if active and active.casefold() in text_fold:
                best_match = {"id": med.get("id"), "name": name, "active": active, "lang": lang}
        if best_match:
            break

    if not best_match and tokens:
        for lang in languages:
            meds = collect_medications(service, lang)
            best_distance = None
            best_candidates = []

            for token in tokens:
                token_norm = normalize_text(token)
                if len(token_norm) < 4:
                    continue
                for med in meds:
                    name = med.get("name", "")
                    if not name:
                        continue
                    name_norm = normalize_text(name)
                    if len(name_norm) < 4:
                        continue
                    distance = levenshtein_distance(token_norm, name_norm, max_distance=2)
                    if distance <= 2:
                        if best_distance is None or distance < best_distance:
                            best_distance = distance
                            best_candidates = [{"token": token, "med": med}]
                        elif distance == best_distance:
                            best_candidates.append({"token": token, "med": med})

            if best_candidates:
                if len(best_candidates) == 1:
                    med = best_candidates[0]["med"]
                    best_match = {
                        "id": med.get("id"),
                        "name": med.get("name"),
                        "active": med.get("active"),
                        "lang": lang
                    }
                else:
                    token = best_candidates[0]["token"]
                    best_match = {
                        "token": token,
                        "lang": lang
                    }
                break

    if not best_match:
        return {}

    if function_name == "get_medication_info":
        if best_match.get("name"):
            return {"query": best_match["name"], "lang": best_match["lang"]}
        if best_match.get("token"):
            return {"query": best_match["token"], "lang": best_match["lang"]}
        return {}
    if function_name == "resolve_medication_id":
        if best_match.get("name"):
            return {"name": best_match["name"], "lang": best_match["lang"]}
        if best_match.get("token"):
            return {"name": best_match["token"], "lang": best_match["lang"]}
        return {}
    if function_name == "search_by_ingredient" and best_match.get("active"):
        return {"ingredient": best_match["active"], "lang": best_match["lang"]}
    if function_name in {"check_stock", "get_handling_warnings"} and best_match.get("id"):
        return {"med_id": best_match["id"]}

    return {}
