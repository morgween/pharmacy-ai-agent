"""abstract base class for medication data sources"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

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
