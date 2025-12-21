"""medication data source implementation using static json file"""
import json
from typing import List, Dict, Optional
from backend.config import settings
from backend.data_sources.base import MedicationDataSource


class MedicationsAPI(MedicationDataSource):
    """static medication data source using medications.json"""

    def __init__(self, data_path: Optional[str] = None):
        """
        initialize medications api

        args:
            data_path: optional path to medications.json, uses config default if none
        """
        self.data_path = data_path or settings.medications_json_path
        self.medications = self._load_medications()

    def _load_medications(self) -> List[Dict]:
        """
        load medications from json file

        returns:
            list of medication dictionaries
        """
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def search_by_ingredient(
        self,
        ingredient: str,
        language: str = 'en'
    ) -> List[Dict]:
        """
        search medications by active ingredient using exact case-insensitive match

        args:
            ingredient: active ingredient name to search
            language: language code (en, he, ru, ar)

        returns:
            list of medication objects matching the ingredient
        """
        results = []
        ingredient_lower = ingredient.lower().strip()

        for med in self.medications:
            active_ing = med.get('active_ingredient', {}).get(language, '')
            if active_ing.lower().strip() == ingredient_lower:
                results.append(med)

        return results

    async def get_medication_by_name(
        self,
        name: str,
        language: str = 'en'
    ) -> Optional[Dict]:
        """
        get medication by name using case-insensitive match

        args:
            name: medication name to search for
            language: language code (en, he, ru, ar)

        returns:
            medication object if found, none otherwise
        """
        name_lower = name.lower().strip()

        for med in self.medications:
            med_name = med.get('names', {}).get(language, '')
            if med_name.lower().strip() == name_lower:
                return med

        return None

    def get_all_medications(self, language: str = 'en') -> List[Dict]:
        """
        get all medications in simplified format for knowledge base

        args:
            language: language code for names and ingredients

        returns:
            list of simplified medication objects
        """
        simplified = []
        for med in self.medications:
            simplified.append({
                'id': med['id'],
                'name': med['names'].get(language, med['names']['en']),
                'active_ingredient': med['active_ingredient'].get(language, med['active_ingredient']['en']),
                'category': med['category'].get(language, med['category']['en']),
                'prescription_required': med.get('prescription_required', False)
            })
        return simplified
