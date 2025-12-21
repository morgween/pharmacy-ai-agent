"""medication data source implementation using sqlalchemy orm"""
import json
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.config import settings
from backend.data_sources.base import MedicationDataSource

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
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        # initialize database if empty
        self._init_db()

    def _init_db(self):
        """
        initialize database and load data if needed

        populates from medications.json if database is empty
        """
        session = self.Session()
        try:
            # check if database is empty
            count = session.query(Medication).count()

            if count == 0:
                # populate from medications.json
                with open(settings.medications_json_path, 'r', encoding='utf-8') as f:
                    medications = json.load(f)

                for med_data in medications:
                    # create medication record
                    med = Medication(
                        id=med_data['id'],
                        dosage=med_data['dosage'],
                        prescription_required=med_data['prescription_required'],
                        price_usd=med_data['price_usd']
                    )

                    # create translations for all languages
                    for lang in ['en', 'he', 'ru', 'ar']:
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

                    session.add(med)

                session.commit()
        finally:
            session.close()

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
        session = self.Session()
        try:
            ingredient_lower = ingredient.lower().strip()

            # query medications with matching ingredient
            medications = (
                session.query(Medication)
                .join(Medication.translations)
                .filter(
                    MedicationI18n.language == language,
                    MedicationI18n.active_ingredient.ilike(ingredient_lower)
                )
                .all()
            )

            # for exact match, filter in python
            results = []
            for med in medications:
                for trans in med.translations:
                    if (trans.language == language and
                        trans.active_ingredient.lower().strip() == ingredient_lower):
                        results.append(self._model_to_dict(med))
                        break

            return results
        finally:
            session.close()

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
        session = self.Session()
        try:
            name_lower = name.lower().strip()

            # query medication with matching name
            medication = (
                session.query(Medication)
                .join(Medication.translations)
                .filter(
                    MedicationI18n.language == language,
                    MedicationI18n.name.ilike(name_lower)
                )
                .first()
            )

            if medication:
                # verify exact match
                for trans in medication.translations:
                    if (trans.language == language and
                        trans.name.lower().strip() == name_lower):
                        return self._model_to_dict(medication)

            return None
        finally:
            session.close()

    def get_all_medications(self, language: str = 'en') -> List[Dict]:
        """
        get all medications in simplified format for knowledge base

        args:
            language: language code for names and ingredients

        returns:
            list of simplified medication objects
        """
        session = self.Session()
        try:
            medications = session.query(Medication).all()

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
        finally:
            session.close()
