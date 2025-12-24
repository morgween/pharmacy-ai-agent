"""agent tool handlers for pharmacy ai agent"""
from typing import Any, Dict, List

from backend.services.tools.medication_tools import MedicationTools
from backend.services.tools.inventory_tools import InventoryTools
from backend.services.tools.pharmacy_tools import PharmacyTools
from backend.services.tools.prescription_tools import PrescriptionTools
from backend.services.tools.handling_tools import HandlingTools


class AgentTools:
    """compose tool handlers used by the agent"""

    def __init__(
        self,
        *,
        medications_api: Any,
        user_db: Any,
        pharmacy_locations: List[Dict[str, Any]],
        format_ambiguous_response
    ) -> None:
        self._medication_tools = MedicationTools(medications_api, format_ambiguous_response)
        self._inventory_tools = InventoryTools()
        self._pharmacy_tools = PharmacyTools(pharmacy_locations)
        self._prescription_tools = PrescriptionTools(user_db, medications_api)
        self._handling_tools = HandlingTools(medications_api)

    async def search_by_ingredient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate ingredient search to medication tools."""
        return await self._medication_tools.search_by_ingredient(args)

    async def resolve_medication_id(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate medication id resolution to medication tools."""
        return await self._medication_tools.resolve_medication_id(args)

    async def get_medication_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate medication info lookup to medication tools."""
        return await self._medication_tools.get_medication_info(args)

    async def check_stock(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate stock check to inventory tools."""
        return await self._inventory_tools.check_stock(args)

    async def find_nearest_pharmacy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate pharmacy search to pharmacy tools."""
        return await self._pharmacy_tools.find_nearest_pharmacy(args)

    async def get_user_prescriptions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate prescription lookup to prescription tools."""
        return await self._prescription_tools.get_user_prescriptions(args)

    async def get_handling_warnings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """delegate handling warnings to handling tools."""
        return await self._handling_tools.get_handling_warnings(args)

