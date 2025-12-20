from abc import ABC, abstractmethod
from typing import Optional, Dict, List

class MedicationDataSource(ABC):
    """Abstract base class for medication data sources"""
    
    @abstractmethod
    async def get_medication_by_name(self, name: str, language: str = 'en') -> Optional[Dict]:
        """Get medication by name"""
        pass
    
    @abstractmethod
    async def check_stock(self, medication_id: str, quantity: int = 1) -> Optional[Dict]:
        """Check stock availability"""
        pass
    
    @abstractmethod
    async def get_prescription_requirements(self, medication_id: str, language: str = 'en') -> Optional[Dict]:
        """Check if prescription is required"""
        pass
    
    @abstractmethod
    async def search_by_ingredient(self, ingredient: str, language: str = 'en') -> List[Dict]:
        """Search medications by active ingredient"""
        pass
