"""medication data source implementation using sqlalchemy orm"""
import asyncio
import json
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.config import settings
from backend.data_sources.base import MedicationDataSource, normalize_text, levenshtein_distance
from backend.constants import SUPPORTED_LANGUAGES
from backend.utils.db_context import get_db_session
from backend.repositories.medication_repository import MedicationRepository

Base = declarative_base()


class Medication(Base):
    """medication table model"""
    __tablename__ = "medications"

    id = Column(String, primary_key=True)
    dosage = Column(String, nullable=False)
    prescription_required = Column(Boolean, nullable=False)
    price_usd = Column(Float, nullable=False)

    # relationship to i18n table
    translations = relationship("MedicationI18n", back_populates="medication", cascade="all, delete-orphan")


class MedicationI18n(Base):
    """medication internationalization table model"""
    __tablename__ = "medication_i18n"

    medication_id = Column(String, ForeignKey("medications.id"), primary_key=True)
    language = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    active_ingredient = Column(String, nullable=False)
    usage_instructions = Column(String, nullable=False)
    warnings = Column(String, nullable=False)
    category = Column(String, nullable=False)

    # relationship to medication table
    medication = relationship("Medication", back_populates="translations")


class MedicationsDB(MedicationDataSource):
    """database-backed medication data source using sqlalchemy"""

    def __init__(self, db_path: Optional[str] = None):
        """
        initialize medications database connection

        args:
            db_path: optional path to sqlite database, uses config default if none
        """
        db_path = db_path or settings.medications_db_path

        # create engine and session
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            pool_pre_ping=True,
            pool_recycle=3600
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._repo = MedicationRepository(Medication, MedicationI18n)

        # initialize database if empty
        self._init_db()

    def _init_db(self):
        """
        initialize database and load data if needed

        populates from medications.json if database is empty or out of sync
        """
        with get_db_session(self.Session, commit=True) as session:
            with open(settings.medications_json_path, 'r', encoding='utf-8') as f:
                medications = json.load(f)

            expected_ids = {med.get("id") for med in medications if med.get("id")}
            existing_ids = set(self._repo.list_medication_ids(session))

            if existing_ids and existing_ids == expected_ids:
                return

            if existing_ids:
                self._repo.clear_all(session)

            for med_data in medications:
                # create medication record
                med = Medication(
                    id=med_data['id'],
                    dosage=med_data['dosage'],
                    prescription_required=med_data['prescription_required'],
                    price_usd=med_data['price_usd']
                )

                # create translations for all languages
                for lang in SUPPORTED_LANGUAGES:
                    i18n = MedicationI18n(
                        medication_id=med_data['id'],
                        language=lang,
                        name=med_data['names'].get(lang, ''),
                        active_ingredient=med_data['active_ingredient'].get(lang, ''),
                        usage_instructions=med_data['usage_instructions'].get(lang, ''),
                        warnings=med_data['warnings'].get(lang, ''),
                        category=med_data['category'].get(lang, '')
                    )
                    med.translations.append(i18n)

                self._repo.add_medication(session, med)

    def _model_to_dict(self, medication: Medication) -> Dict:
        """
        convert sqlalchemy model to medication dictionary

        args:
            medication: medication model instance with translations loaded

        returns:
            medication dictionary with multilingual fields
        """
        result = {
            'id': medication.id,
            'dosage': medication.dosage,
            'prescription_required': medication.prescription_required,
            'price_usd': medication.price_usd,
            'names': {},
            'active_ingredient': {},
            'usage_instructions': {},
            'warnings': {},
            'category': {}
        }

        for trans in medication.translations:
            result['names'][trans.language] = trans.name
            result['active_ingredient'][trans.language] = trans.active_ingredient
            result['usage_instructions'][trans.language] = trans.usage_instructions
            result['warnings'][trans.language] = trans.warnings
            result['category'][trans.language] = trans.category

        return result

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
        return await asyncio.to_thread(
            self._search_by_ingredient_sync,
            ingredient,
            language
        )

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
        return await asyncio.to_thread(
            self._get_medication_by_name_sync,
            name,
            language
        )

    async def get_medication_by_id(self, med_id: str) -> Optional[Dict]:
        """
        get medication by id

        args:
            med_id: medication id

        returns:
            medication object if found, none otherwise
        """
        return await asyncio.to_thread(self._get_medication_by_id_sync, med_id)

    def _search_by_ingredient_sync(
        self,
        ingredient: str,
        language: str
    ) -> List[Dict]:
        """run ingredient search in a sync session for async wrapper."""
        with get_db_session(self.Session) as session:
            ingredient_lower = ingredient.lower().strip()

            # query medications with matching ingredient
            medications = self._repo.find_by_ingredient(session, language, ingredient_lower)

            # for exact match, filter in python
            results = []
            for med in medications:
                for trans in med.translations:
                    if (trans.language == language and
                        trans.active_ingredient.lower().strip() == ingredient_lower):
                        results.append(self._model_to_dict(med))
                        break

            return results

    def _get_medication_by_name_sync(
        self,
        name: str,
        language: str
    ) -> Optional[Dict]:
        """resolve a medication by name using sync session queries."""
        with get_db_session(self.Session) as session:
            name_lower = name.lower().strip()

            # query medication with matching name
            medication = self._repo.find_by_name(session, language, name_lower)

            if medication:
                # verify exact match
                for trans in medication.translations:
                    if (trans.language == language and
                        trans.name.lower().strip() == name_lower):
                        return self._model_to_dict(medication)

            normalized_target = normalize_text(name)
            if not normalized_target:
                return None

            translations = self._repo.list_translations(session, language)

            candidates = []
            for trans in translations:
                if not trans.name:
                    continue
                distance = levenshtein_distance(
                    normalized_target,
                    normalize_text(trans.name),
                    max_distance=2
                )
                if distance <= 2:
                    candidates.append((distance, trans.medication_id, trans.name))

            if not candidates:
                return None

            best_by_id = {}
            for distance, med_id, med_name in candidates:
                current = best_by_id.get(med_id)
                if current is None or distance < current["distance"]:
                    best_by_id[med_id] = {
                        "distance": distance,
                        "name": med_name
                    }

            if len(best_by_id) > 1:
                return {
                    "_ambiguous": True,
                    "candidates": [
                        {
                            "id": med_id,
                            "name": entry["name"],
                            "distance": entry["distance"]
                        }
                        for med_id, entry in best_by_id.items()
                    ]
                }

            med_id = next(iter(best_by_id))
            medication = self._repo.get_by_id(session, med_id)
            if medication:
                return self._model_to_dict(medication)

            return None

    def _get_medication_by_id_sync(self, med_id: str) -> Optional[Dict]:
        """load medication by id using a sync session."""
        if not med_id:
            return None

        with get_db_session(self.Session) as session:
            medication = self._repo.get_by_id(session, med_id)
            if medication:
                return self._model_to_dict(medication)
            return None

    def get_all_medications(self, language: str = 'en') -> List[Dict]:
        """
        get all medications in simplified format for knowledge base

        args:
            language: language code for names and ingredients

        returns:
            list of simplified medication objects
        """
        with get_db_session(self.Session) as session:
            medications = self._repo.list_all(session)

            simplified = []
            for med in medications:
                # get translation for requested language
                trans_dict = {}
                for trans in med.translations:
                    if trans.language == language:
                        trans_dict = {
                            'name': trans.name,
                            'active_ingredient': trans.active_ingredient,
                            'category': trans.category
                        }
                        break

                if trans_dict:
                    simplified.append({
                        'id': med.id,
                        'name': trans_dict['name'],
                        'active_ingredient': trans_dict['active_ingredient'],
                        'category': trans_dict['category'],
                        'prescription_required': med.prescription_required
                    })

            return simplified
