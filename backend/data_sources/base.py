"""abstract base class for medication data sources"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalize text for matching across minor typos and formatting."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.casefold().strip()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[^\w]", "", normalized, flags=re.UNICODE)
    return normalized


def levenshtein_distance(a: str, b: str, max_distance: Optional[int] = None) -> int:
    """Compute Levenshtein distance with optional early exit."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1

    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current_row = [i]
        row_min = current_row[0]
        for j, cb in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j - 1] + (0 if ca == cb else 1)
            cell = min(insert_cost, delete_cost, replace_cost)
            current_row.append(cell)
            if cell < row_min:
                row_min = cell

        if max_distance is not None and row_min > max_distance:
            return max_distance + 1
        prev_row = current_row

    return prev_row[-1]

class MedicationDataSource(ABC):
    """abstract base class defining interface for medication data operations"""

    @abstractmethod
    async def get_medication_by_name(self, name: str, language: str = 'en') -> Optional[Dict]:
        """
        get medication by name using case-insensitive match

        args:
            name: medication name to search for
            language: language code (en, he, ru, ar)

        returns:
            medication object if found, none otherwise
        """
        pass

    @abstractmethod
    async def get_medication_by_id(self, med_id: str) -> Optional[Dict]:
        """
        get medication by id

        args:
            med_id: medication id

        returns:
            medication object if found, none otherwise
        """
        pass

    @abstractmethod
    async def search_by_ingredient(self, ingredient: str, language: str = 'en') -> List[Dict]:
        """
        search medications by active ingredient

        args:
            ingredient: active ingredient name to search
            language: language code (en, he, ru, ar)

        returns:
            list of medication objects matching the ingredient
        """
        pass
