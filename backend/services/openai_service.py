"""openai service for pharmacy ai agent with function calling"""
import json
import os
import httpx
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.config import settings
from backend.prompts import build_system_prompt


class OpenAIAgentService:
    """service for openai agent with function calling and medication knowledge base"""

    def __init__(self):
        """initialize openai agent service with client and tools"""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        # use configured data source (api or db)
        if settings.medication_data_source == "db":
            from backend.data_sources.medications_db import MedicationsDB
            self.medications_api = MedicationsDB()
        else:
            from backend.data_sources.medications_api import MedicationsAPI
            self.medications_api = MedicationsAPI()

        self.tools = self._load_tool_schemas()

    def _load_tool_schemas(self) -> List[Dict]:
        """
        load all tool schemas from configured directory

        returns:
            list of tool schema dictionaries
        """
        schemas = []

        for filename in settings.allowed_tools:
            filepath = os.path.join(settings.tool_schemas_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    schemas.append(json.load(f))

        return schemas

    async def execute_function_call(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        execute a function call and return results

        args:
            function_name: name of the function to execute
            arguments: function arguments as dict

        returns:
            function execution result dict
        """
        if function_name == "search_by_ingredient":
            return await self._search_by_ingredient(arguments)
        elif function_name == "resolve_medication_id":
            return await self._resolve_medication_id(arguments)
        elif function_name == "get_medication_info":
            return await self._get_medication_info(arguments)
        elif function_name == "check_stock":
            return await self._check_stock(arguments)
        else:
            return {"error": f"unknown function: {function_name}"}

    async def _search_by_ingredient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute search_by_ingredient function

        args:
            args: dictionary containing ingredient and lang parameters

        returns:
            search results with matching medications
        """
        ingredient = args.get('ingredient')
        lang = args.get('lang', 'en')

        if not ingredient:
            return {"success": False, "error": "missing required parameter: ingredient"}

        results = await self.medications_api.search_by_ingredient(
            ingredient=ingredient,
            language=lang
        )

        if not results:
            return {
                "success": True,
                "matches": 0,
                "medications": [],
                "message": f"no medications found with active ingredient '{ingredient}'"
            }

        return {
            "success": True,
            "matches": len(results),
            "medications": [
                {
                    "id": med['id'],
                    "name": med['names'][lang],
                    "active_ingredient": med['active_ingredient'][lang],
                    "dosage": med['dosage'],
                    "prescription_required": med['prescription_required'],
                    "price_usd": med['price_usd'],
                    "category": med['category'][lang]
                }
                for med in results
            ]
        }

    async def _resolve_medication_id(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute resolve_medication_id function

        args:
            args: dictionary containing name and lang parameters

        returns:
            medication id if found
        """
        name = args.get('name')
        lang = args.get('lang', 'en')

        if not name:
            return {"success": False, "error": "missing required parameter: name"}

        med = await self.medications_api.get_medication_by_name(
            name=name,
            language=lang
        )

        if med:
            return {
                "success": True,
                "id": med['id'],
                "name": med['names'][lang]
            }

        return {
            "success": False,
            "message": f"medication '{name}' not found"
        }

    async def _get_medication_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute get_medication_info function

        args:
            args: dictionary containing query and optional lang parameters

        returns:
            full medication information
        """
        query = args.get('query')
        lang = args.get('lang', 'en')

        if not query:
            return {"success": False, "error": "missing required parameter: query"}

        # try to find by id first, then by name
        med = None
        for m in self.medications_api.medications:
            if m['id'] == query:
                med = m
                break

        if not med:
            med = await self.medications_api.get_medication_by_name(
                name=query,
                language=lang
            )

        if not med:
            return {
                "success": False,
                "message": f"medication '{query}' not found"
            }

        return {
            "success": True,
            "medication": {
                "id": med['id'],
                "name": med['names'][lang],
                "active_ingredient": med['active_ingredient'][lang],
                "dosage": med['dosage'],
                "prescription_required": med['prescription_required'],
                "usage_instructions": med['usage_instructions'][lang],
                "warnings": med['warnings'][lang],
                "category": med['category'][lang],
                "price_usd": med['price_usd']
            }
        }

    async def _check_stock(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute check_stock function by calling inventory api

        args:
            args: dictionary containing med_id parameter

        returns:
            boolean availability status (not exact quantity)
        """
        med_id = args.get('med_id')

        if not med_id:
            return {"success": False, "error": "missing required parameter: med_id"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.inventory_service_url}/check_stock/{med_id}",
                    timeout=settings.openai_timeout
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "id": data['id'],
                    "in_stock": data['in_stock']
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"medication {med_id} not found in inventory"
                }
            return {
                "success": False,
                "error": f"inventory api error: {e.response.status_code}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"failed to check stock: {str(e)}"
            }

    def build_system_prompt(self, language: str = 'en') -> str:
        """
        build system prompt with embedded medication knowledge base

        args:
            language: language code for medication names and details

        returns:
            system prompt string with policies and available tools
        """
        knowledge_base = self.medications_api.get_all_medications(language)
        return build_system_prompt(knowledge_base, language)
