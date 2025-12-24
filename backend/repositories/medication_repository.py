"""data access layer for medication models"""
from __future__ import annotations

from typing import Iterable, List, Optional, Type, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from backend.data_sources.medications_db import Medication, MedicationI18n


class MedicationRepository:
    """repository for medication database operations"""

    def __init__(self, medication_cls: Type, i18n_cls: Type) -> None:
        self._Medication = medication_cls
        self._MedicationI18n = i18n_cls

    def list_medication_ids(self, session: Session) -> Iterable[str]:
        """return all medication ids from storage."""
        return [row[0] for row in session.query(self._Medication.id).all()]

    def clear_all(self, session: Session) -> None:
        """remove all medications and translations."""
        session.query(self._MedicationI18n).delete()
        session.query(self._Medication).delete()

    def add_medication(self, session: Session, medication) -> None:
        """persist a medication row with attached translations."""
        session.add(medication)

    def find_by_name(
        self,
        session: Session,
        language: str,
        name_lower: str
    ) -> Optional[Medication]:
        """find medication by localized name using ilike."""
        return (
            session.query(self._Medication)
            .join(self._Medication.translations)
            .filter(
                self._MedicationI18n.language == language,
                self._MedicationI18n.name.ilike(name_lower)
            )
            .first()
        )

    def find_by_ingredient(
        self,
        session: Session,
        language: str,
        ingredient_lower: str
    ) -> List[Medication]:
        """find medications by localized active ingredient."""
        return (
            session.query(self._Medication)
            .join(self._Medication.translations)
            .filter(
                self._MedicationI18n.language == language,
                self._MedicationI18n.active_ingredient.ilike(ingredient_lower)
            )
            .all()
        )

    def list_translations(self, session: Session, language: str) -> List[MedicationI18n]:
        """list translation rows for a single language."""
        return (
            session.query(self._MedicationI18n)
            .filter(self._MedicationI18n.language == language)
            .all()
        )

    def get_by_id(self, session: Session, med_id: str) -> Optional[Medication]:
        """get medication by primary id."""
        return session.query(self._Medication).filter(self._Medication.id == med_id).first()

    def list_all(self, session: Session) -> List[Medication]:
        """list all medication rows."""
        return session.query(self._Medication).all()
