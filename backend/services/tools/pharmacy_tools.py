"""pharmacy location tool handlers"""
import logging
import re
from typing import Dict, Any, List

from backend.data_sources.base import normalize_text, levenshtein_distance
from backend.i18n.messages import Messages
from backend.utils.response import tool_error_handler

logger = logging.getLogger(__name__)


class PharmacyTools:
    """pharmacy location tools"""

    def __init__(self, pharmacy_locations: List[Dict[str, Any]]) -> None:
        self._pharmacy_locations = pharmacy_locations

    @tool_error_handler(error_key="search_failed", message_category="PHARMACY")
    async def find_nearest_pharmacy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        tool: find_nearest_pharmacy
        purpose: return nearby pharmacy locations for a city or zip code.

        inputs:
            city (str, optional): city name to search.
            zip_code (str, optional): zip/postal code to search.
            lang (str, optional): language code, defaults to "en".

        output schema:
            success (bool)
            location_not_found (bool)
            searched_location (str)
            suggested_city (str, optional)
            count (int)
            pharmacies (list[dict])
                - id (str)
                - name (str)
                - address (str)
                - city (str)
                - zip_code (str)
                - phone (str)
                - hours (str)
                - services (list[str] or str)
            message (str)
            error (str, optional) on failure

        error handling:
            - missing city/zip returns success false with error "missing_location".
            - unexpected exceptions are handled by tool_error_handler -> error "search_failed".

        fallback behavior:
            - fuzzy match is attempted on city names (levenshtein <= 2).
            - city aliases can map to the nearest known city.
            - when no locations found, returns success true, count 0, and available cities list.
        """
        zip_code = args.get('zip_code')
        city = args.get('city')
        lang = args.get('lang', 'en')

        if not zip_code and not city:
            logger.warning("find_nearest_pharmacy called without location parameters")
            return {
                "success": False,
                "error": "missing_location",
                "message": Messages.get("PHARMACY", "missing_location", lang)
            }

        # use cached pharmacy locations instead of reading from disk
        pharmacy_locations = self._pharmacy_locations

        # filter by zip_code or city if provided
        filtered_locations = pharmacy_locations
        searched_location = zip_code or city
        location_not_found = False
        suggested_city = None

        if zip_code:
            filtered_locations = [p for p in pharmacy_locations if zip_code in p.get('zip_code', '')]
        elif city:
            filtered_locations = [p for p in pharmacy_locations if city.lower() in p.get('city', '').lower()]

        if not filtered_locations and city:
            city_norm = normalize_text(city)
            tokens = [
                normalize_text(token)
                for token in re.findall(r"[A-Za-z\u0590-\u05FF\u0400-\u04FF\u0600-\u06FF]+", city)
            ]
            available_cities = list(set(p.get('city', '') for p in pharmacy_locations))
            best_distance = None
            best_candidates = []

            for candidate in available_cities:
                candidate_norm = normalize_text(candidate)
                if not candidate_norm:
                    continue
                distances = []
                if city_norm:
                    distances.append(
                        levenshtein_distance(city_norm, candidate_norm, max_distance=2)
                    )
                for token in tokens:
                    if token:
                        distances.append(
                            levenshtein_distance(token, candidate_norm, max_distance=2)
                        )
                min_distance = min(distances) if distances else None
                if min_distance is None or min_distance > 2:
                    continue
                if best_distance is None or min_distance < best_distance:
                    best_distance = min_distance
                    best_candidates = [candidate]
                elif min_distance == best_distance:
                    best_candidates.append(candidate)

            if len(best_candidates) == 1:
                matched_city = best_candidates[0]
                filtered_locations = [
                    p for p in pharmacy_locations if p.get('city', '').lower() == matched_city.lower()
                ]
                searched_location = matched_city
                location_not_found = False

        if not filtered_locations and city:
            city_norm = normalize_text(city)
            alias_city_counts: Dict[str, int] = {}
            for pharmacy in pharmacy_locations:
                for alias in pharmacy.get("nearby_cities", []) or []:
                    if normalize_text(alias) == city_norm:
                        alias_city = pharmacy.get("city", "")
                        if alias_city:
                            alias_city_counts[alias_city] = alias_city_counts.get(alias_city, 0) + 1
                        break
            if alias_city_counts:
                suggested_city = max(alias_city_counts, key=alias_city_counts.get)
                filtered_locations = [
                    p for p in pharmacy_locations if p.get('city', '').lower() == suggested_city.lower()
                ]
                location_not_found = True

        # if no match found, indicate this and ask for another location
        if not filtered_locations and searched_location:
            location_not_found = True
            available_cities = list(set(p.get('city', '') for p in pharmacy_locations))
            logger.info(f"no pharmacies found in '{searched_location}', available cities: {available_cities}")
            message = Messages.get(
                "PHARMACY",
                "not_found",
                lang,
                searched_location=searched_location,
                available=", ".join(sorted(available_cities))
            )
            return {
                "success": True,
                "location_not_found": True,
                "searched_location": searched_location,
                "count": 0,
                "pharmacies": [],
                "message": message
            }

        logger.info(f"found {len(filtered_locations)} pharmacies near {searched_location}")

        # format hours into a simple summary string
        def format_hours(hours_dict):
            """format hours dict into a compact display string."""
            return f"Sun: {hours_dict.get('sunday', 'Closed')}, Mon-Thu: {hours_dict.get('monday', 'Closed')}, Fri: {hours_dict.get('friday', 'Closed')}, Sat: {hours_dict.get('saturday', 'Closed')}"

        # format response
        formatted_pharmacies = [{
            "id": p["id"],
            "name": p["name"],
            "address": p["address"],
            "city": p["city"],
            "zip_code": p["zip_code"],
            "phone": p["phone"],
            "hours": format_hours(p["hours"]),
            "services": p["services"]
        } for p in filtered_locations[:5]]

        message_key = "found"
        message_kwargs = {
            "count": len(filtered_locations),
            "name": formatted_pharmacies[0]["name"],
            "address": formatted_pharmacies[0]["address"]
        }
        if suggested_city:
            message_key = "fallback_nearest"
            message_kwargs.update({
                "searched_location": city,
                "suggested_city": suggested_city
            })
        message = Messages.get("PHARMACY", message_key, lang, **message_kwargs)

        return {
            "success": True,
            "location_not_found": location_not_found,
            "searched_location": searched_location,
            "suggested_city": suggested_city,
            "count": len(filtered_locations),
            "pharmacies": formatted_pharmacies,
            "message": message
        }
