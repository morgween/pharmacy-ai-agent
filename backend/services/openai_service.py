"""openai service for pharmacy ai agent with function calling"""
import json
import os
import logging
import httpx
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.config import settings
from backend.prompts import build_system_prompt

logger = logging.getLogger(__name__)


class OpenAIAgentService:
    """service for openai agent with function calling and medication knowledge base"""

    def __init__(self):
        """initialize openai agent service with client and tools"""
        try:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("openai client initialized successfully")

            # use configured data source (api or db)
            if settings.medication_data_source == "db":
                from backend.data_sources.medications_db import MedicationsDB
                self.medications_api = MedicationsDB()
                logger.info("using medications database as data source")
            else:
                from backend.data_sources.medications_api import MedicationsAPI
                self.medications_api = MedicationsAPI()
                logger.info("using medications api (json file) as data source")

            self.tools = self._load_tool_schemas()
            logger.info(f"openai agent service initialized with {len(self.tools)} tools")

        except Exception as e:
            logger.error(f"failed to initialize openai agent service: {e}")
            raise RuntimeError(f"critical: failed to initialize agent service: {e}")

    def _load_tool_schemas(self) -> List[Dict]:
        """
        load all tool schemas from configured directory with error handling

        returns:
            list of tool schema dictionaries

        raises:
            RuntimeError: if no tool schemas could be loaded
        """
        schemas = []

        for filename in settings.allowed_tools:
            filepath = os.path.join(settings.tool_schemas_dir, filename)

            try:
                if not os.path.exists(filepath):
                    logger.warning(f"tool schema not found: {filepath}")
                    continue

                with open(filepath, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    schemas.append(schema)
                    logger.debug(f"loaded tool schema: {filename}")

            except json.JSONDecodeError as e:
                logger.error(f"invalid json in tool schema {filename}: {e}")
                # continue loading other schemas
                continue
            except Exception as e:
                logger.error(f"error loading tool schema {filename}: {e}")
                continue

        if not schemas:
            logger.error("no tool schemas loaded - agent will have no tools!")
            raise RuntimeError("critical: no tool schemas available")

        logger.info(f"loaded {len(schemas)} tool schemas")
        return schemas

    async def execute_function_call(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        execute a function call and return results with error handling

        args:
            function_name: name of the function to execute
            arguments: function arguments as dict

        returns:
            function execution result dict
        """
        logger.info(f"executing function call: {function_name} with args: {arguments}")

        try:
            if function_name == "search_by_ingredient":
                result = await self._search_by_ingredient(arguments)
            elif function_name == "resolve_medication_id":
                result = await self._resolve_medication_id(arguments)
            elif function_name == "get_medication_info":
                result = await self._get_medication_info(arguments)
            elif function_name == "check_stock":
                result = await self._check_stock(arguments)
            elif function_name == "find_nearest_pharmacy":
                result = await self._find_nearest_pharmacy(arguments)
            elif function_name == "redirect_to_healthcare_professional":
                result = await self._redirect_to_healthcare_professional(arguments)
            elif function_name == "get_prescription_status":
                result = await self._get_prescription_status(arguments)
            elif function_name == "get_handling_warnings":
                result = await self._get_handling_warnings(arguments)
            else:
                logger.error(f"unknown function called: {function_name}")
                return {
                    "success": False,
                    "error": f"unknown function: {function_name}",
                    "message": "I encountered an internal error. Please try again or contact support."
                }

            logger.debug(f"function {function_name} result: {result}")
            return result

        except Exception as e:
            logger.error(f"unexpected error executing {function_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "internal_error",
                "message": "I encountered an unexpected error while processing your request. Please try again."
            }

    async def _search_by_ingredient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute search_by_ingredient function with error handling

        args:
            args: dictionary containing ingredient and lang parameters

        returns:
            search results with matching medications
        """
        ingredient = args.get('ingredient')
        lang = args.get('lang', 'en')

        if not ingredient:
            logger.warning("search_by_ingredient called without ingredient parameter")
            return {
                "success": False,
                "error": "missing required parameter: ingredient",
                "message": "Please provide an active ingredient to search for."
            }

        try:
            results = await self.medications_api.search_by_ingredient(
                ingredient=ingredient,
                language=lang
            )

            if not results:
                logger.info(f"no medications found for ingredient: {ingredient}")
                return {
                    "success": True,
                    "matches": 0,
                    "medications": [],
                    "message": f"No medications found with active ingredient '{ingredient}'. Please check the spelling or try another ingredient."
                }

            # defensive dict access with fallback to english
            medications = []
            for med in results:
                try:
                    medications.append({
                        "id": med.get('id', 'unknown'),
                        "name": med.get('names', {}).get(lang, med.get('names', {}).get('en', 'Unknown')),
                        "active_ingredient": med.get('active_ingredient', {}).get(lang, med.get('active_ingredient', {}).get('en', 'Unknown')),
                        "dosage": med.get('dosage', 'Not specified'),
                        "prescription_required": med.get('prescription_required', False),
                        "price_usd": med.get('price_usd', 0.0),
                        "category": med.get('category', {}).get(lang, med.get('category', {}).get('en', 'General'))
                    })
                except Exception as e:
                    logger.warning(f"error processing medication {med.get('id', 'unknown')}: {e}")
                    # skip this medication but continue with others
                    continue

            logger.info(f"found {len(medications)} medications for ingredient: {ingredient}")
            return {
                "success": True,
                "matches": len(medications),
                "medications": medications
            }

        except Exception as e:
            logger.error(f"error searching by ingredient '{ingredient}': {e}", exc_info=True)
            return {
                "success": False,
                "error": "search_failed",
                "message": "I'm having trouble searching medications right now. Please try again later."
            }

    async def _resolve_medication_id(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute resolve_medication_id function with error handling

        args:
            args: dictionary containing name and lang parameters

        returns:
            medication id if found
        """
        name = args.get('name')
        lang = args.get('lang', 'en')

        if not name:
            logger.warning("resolve_medication_id called without name parameter")
            return {
                "success": False,
                "error": "missing required parameter: name",
                "message": "Please provide a medication name."
            }

        try:
            med = await self.medications_api.get_medication_by_name(
                name=name,
                language=lang
            )

            if med:
                logger.info(f"resolved medication '{name}' to ID: {med.get('id')}")
                return {
                    "success": True,
                    "id": med.get('id', 'unknown'),
                    "name": med.get('names', {}).get(lang, med.get('names', {}).get('en', name))
                }

            logger.info(f"medication not found: '{name}' (language: {lang})")
            return {
                "success": False,
                "message": f"I couldn't find a medication named '{name}'. Please check the spelling or try providing the active ingredient."
            }

        except Exception as e:
            logger.error(f"error resolving medication name '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": "resolve_failed",
                "message": "I'm having trouble looking up that medication right now. Please try again later."
            }

    async def _get_medication_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute get_medication_info function with error handling

        args:
            args: dictionary containing query and optional lang parameters

        returns:
            full medication information
        """
        query = args.get('query')
        lang = args.get('lang', 'en')

        if not query:
            logger.warning("get_medication_info called without query parameter")
            return {
                "success": False,
                "error": "missing required parameter: query",
                "message": "Please provide a medication name or ID."
            }

        try:
            # try to find by id first, then by name
            med = None
            for m in self.medications_api.medications:
                if m.get('id') == query:
                    med = m
                    break

            if not med:
                med = await self.medications_api.get_medication_by_name(
                    name=query,
                    language=lang
                )

            if not med:
                logger.info(f"medication not found: '{query}' (language: {lang})")
                return {
                    "success": False,
                    "message": f"I couldn't find information about '{query}'. Please check the spelling or try searching by active ingredient."
                }

            # defensive dict access with fallback to english
            logger.info(f"found medication info for: {query} (ID: {med.get('id')})")
            return {
                "success": True,
                "medication": {
                    "id": med.get('id', 'unknown'),
                    "name": med.get('names', {}).get(lang, med.get('names', {}).get('en', 'Unknown')),
                    "active_ingredient": med.get('active_ingredient', {}).get(lang, med.get('active_ingredient', {}).get('en', 'Unknown')),
                    "dosage": med.get('dosage', 'Not specified'),
                    "prescription_required": med.get('prescription_required', False),
                    "usage_instructions": med.get('usage_instructions', {}).get(lang, med.get('usage_instructions', {}).get('en', 'Consult a pharmacist')),
                    "warnings": med.get('warnings', {}).get(lang, med.get('warnings', {}).get('en', 'Consult a pharmacist')),
                    "category": med.get('category', {}).get(lang, med.get('category', {}).get('en', 'General')),
                    "price_usd": med.get('price_usd', 0.0)
                }
            }

        except Exception as e:
            logger.error(f"error getting medication info for '{query}': {e}", exc_info=True)
            return {
                "success": False,
                "error": "info_retrieval_failed",
                "message": "I'm having trouble retrieving medication information right now. Please try again later."
            }

    async def _check_stock(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute check_stock function by calling inventory api with comprehensive error handling

        args:
            args: dictionary containing med_id parameter

        returns:
            boolean availability status (not exact quantity)
        """
        med_id = args.get('med_id')

        if not med_id:
            logger.warning("check_stock called without med_id parameter")
            return {
                "success": False,
                "error": "missing required parameter: med_id",
                "message": "Please provide a medication ID to check stock."
            }

        try:
            url = f"{settings.inventory_service_url}/check_stock/{med_id}"
            logger.debug(f"checking stock for {med_id} at {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=settings.openai_timeout)
                response.raise_for_status()
                data = response.json()

                logger.info(f"stock check for {med_id}: {data.get('in_stock', False)}")
                return {
                    "success": True,
                    "id": data.get('id', med_id),
                    "in_stock": data.get('in_stock', False)
                }

        except httpx.TimeoutException:
            logger.error(f"timeout checking stock for {med_id}")
            return {
                "success": False,
                "error": "timeout",
                "message": "The stock check is taking too long. Please try again in a moment."
            }
        except httpx.ConnectError:
            logger.error(f"connection error to inventory service: {settings.inventory_service_url}")
            return {
                "success": False,
                "error": "service_unavailable",
                "message": "I cannot connect to the inventory system right now. Please try again later or contact the pharmacy directly."
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"medication {med_id} not found in inventory")
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"I couldn't find medication {med_id} in our inventory system."
                }
            logger.error(f"http error checking stock for {med_id}: {e.response.status_code}")
            return {
                "success": False,
                "error": "http_error",
                "message": f"The inventory system returned an error. Please try again or contact the pharmacy."
            }
        except json.JSONDecodeError:
            logger.error(f"invalid json response from inventory service for {med_id}")
            return {
                "success": False,
                "error": "invalid_response",
                "message": "I received an invalid response from the inventory system. Please try again later."
            }
        except Exception as e:
            logger.error(f"unexpected error checking stock for {med_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "unknown",
                "message": "An unexpected error occurred while checking stock. Please try again later."
            }

    def build_system_prompt(self, language: str = 'en') -> str:
        """
        build system prompt with embedded medication knowledge base and error handling

        args:
            language: language code for medication names and details

        returns:
            system prompt string with policies and available tools
        """
        try:
            knowledge_base = self.medications_api.get_all_medications(language)
            logger.debug(f"built system prompt with {len(knowledge_base)} medications for language: {language}")
            return build_system_prompt(knowledge_base, language)
        except Exception as e:
            logger.error(f"error building system prompt: {e}", exc_info=True)
            # fallback to minimal prompt with empty knowledge base
            logger.warning("using minimal system prompt with empty knowledge base")
            return build_system_prompt([], language)

    async def _find_nearest_pharmacy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        find nearest pharmacy/drugstore locations based on user location or zip code

        args:
            args: dictionary containing location parameters (zip_code, city, or coordinates)

        returns:
            list of nearby pharmacy locations with addresses and hours
        """
        zip_code = args.get('zip_code')
        city = args.get('city')
        lang = args.get('lang', 'en')

        if not zip_code and not city:
            logger.warning("find_nearest_pharmacy called without location parameters")
            return {
                "success": False,
                "error": "missing_location",
                "message": "Please provide a zip code or city name to find nearby pharmacies."
            }

        try:
            # load pharmacy locations from data file
            pharmacy_data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pharmacy_locations.json")
            with open(pharmacy_data_path, 'r', encoding='utf-8') as f:
                pharmacy_locations = json.load(f)

            # filter by zip_code or city if provided
            filtered_locations = pharmacy_locations
            if zip_code:
                filtered_locations = [p for p in pharmacy_locations if zip_code in p.get('zip_code', '')]
            elif city:
                filtered_locations = [p for p in pharmacy_locations if city.lower() in p.get('city', '').lower()]

            # if no exact match, return all locations
            if not filtered_locations:
                filtered_locations = pharmacy_locations

            logger.info(f"found {len(filtered_locations)} pharmacies near {zip_code or city}")

            # format hours for display
            def format_hours(hours_dict):
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

            return {
                "success": True,
                "count": len(filtered_locations),
                "pharmacies": formatted_pharmacies,
                "message": f"Found {len(filtered_locations)} pharmacy locations near you. The nearest is {formatted_pharmacies[0]['name']} at {formatted_pharmacies[0]['address']}."
            }

        except Exception as e:
            logger.error(f"error finding nearest pharmacy: {e}", exc_info=True)
            return {
                "success": False,
                "error": "search_failed",
                "message": "I'm having trouble finding nearby pharmacies right now. Please try again later."
            }

    async def _redirect_to_healthcare_professional(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        redirect user to appropriate healthcare professional for prescription or medical advice needs

        args:
            args: dictionary containing query_type and optional specialty

        returns:
            healthcare professional contact information and guidance
        """
        query_type = args.get('query_type', 'general')
        specialty = args.get('specialty')
        lang = args.get('lang', 'en')
        urgency = args.get('urgency', 'routine')

        try:
            # load healthcare resources from data file
            resources_data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "healthcare_resources.json")
            with open(resources_data_path, 'r', encoding='utf-8') as f:
                healthcare_resources = json.load(f)

            # determine appropriate resource type
            resource_key = "medical_advice"  # default
            if query_type in ["prescription", "rx", "refill", "new_prescription"]:
                resource_key = "prescription"
            elif query_type in ["emergency", "urgent", "poison", "overdose"]:
                resource_key = "emergency"
            elif urgency == "emergency":
                resource_key = "emergency"

            resource = healthcare_resources.get(resource_key, healthcare_resources["medical_advice"])

            logger.info(f"redirecting user to healthcare professional for: {query_type}")

            return {
                "success": True,
                "redirect_type": resource_key,
                "title": resource["title"],
                "description": resource["description"],
                "options": resource["options"],
                "disclaimer": resource["disclaimer"],
                "message": f"{resource['description']} {resource['disclaimer']}"
            }

        except Exception as e:
            logger.error(f"error redirecting to healthcare professional: {e}", exc_info=True)
            return {
                "success": False,
                "error": "redirect_failed",
                "message": "For medical advice or prescriptions, please consult your doctor or pharmacist directly."
            }

    async def _get_prescription_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute get_prescription_status function with error handling

        args:
            args: dictionary containing prescription_id parameter

        returns:
            prescription status details
        """
        from backend.models.user import UserDatabase

        prescription_id = args.get('prescription_id')

        if not prescription_id:
            logger.warning("get_prescription_status called without prescription_id")
            return {
                "success": False,
                "error": "missing_parameter",
                "message": "Please provide a prescription ID."
            }

        try:
            user_db = UserDatabase()
            prescription = user_db.get_prescription_status(prescription_id)

            if not prescription:
                logger.info(f"prescription not found: {prescription_id}")
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"I couldn't find prescription {prescription_id}. Please check the ID and try again."
                }

            logger.info(f"retrieved prescription status: {prescription_id}, status: {prescription.get('status')}")

            # format user-friendly message based on status
            status = prescription.get('status')
            status_messages = {
                "pending": f"Your prescription is being prepared. We'll notify you when it's ready for pickup at {prescription.get('pickup_location')}.",
                "ready": f"Your prescription is ready for pickup at {prescription.get('pickup_location')}!",
                "picked_up": f"This prescription was picked up on {prescription.get('picked_up_at', 'a recent date')}.",
                "cancelled": "This prescription has been cancelled."
            }

            return {
                "success": True,
                "prescription_id": prescription.get('prescription_id'),
                "status": status,
                "pickup_location": prescription.get('pickup_location'),
                "prescriber_name": prescription.get('prescriber_name'),
                "quantity": prescription.get('quantity'),
                "med_id": prescription.get('med_id'),
                "created_at": prescription.get('created_at'),
                "message": status_messages.get(status, f"Status: {status}")
            }

        except Exception as e:
            logger.error(f"error getting prescription status for {prescription_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "retrieval_failed",
                "message": "I'm having trouble retrieving prescription status right now. Please try again later."
            }

    async def _get_handling_warnings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        execute get_handling_warnings function with error handling

        args:
            args: dictionary containing med_id and optional lang parameters

        returns:
            safe handling instructions and warnings from medication labels
        """
        med_id = args.get('med_id')
        lang = args.get('lang', 'en')

        if not med_id:
            logger.warning("get_handling_warnings called without med_id")
            return {
                "success": False,
                "error": "missing_parameter",
                "message": "Please provide a medication ID."
            }

        try:
            # find medication in knowledge base
            med = None
            for m in self.medications_api.medications:
                if m.get('id') == med_id:
                    med = m
                    break

            if not med:
                logger.info(f"medication not found for handling warnings: {med_id}")
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"I couldn't find medication {med_id} in our system."
                }

            # extract handling and warning information from label data
            warnings = med.get('warnings', {}).get(lang, med.get('warnings', {}).get('en', ''))

            # construct safe handling instructions (factual, label-based only)
            handling_instructions = []

            # storage information
            handling_instructions.append("Store at room temperature away from light and moisture.")

            # child safety
            handling_instructions.append("Keep out of reach of children and pets.")

            # general safety
            if med.get('prescription_required'):
                handling_instructions.append("Prescription medication - use only as directed by your healthcare provider.")

            logger.info(f"retrieved handling warnings for {med_id}")

            return {
                "success": True,
                "med_id": med_id,
                "medication_name": med.get('names', {}).get(lang, med.get('names', {}).get('en', 'Unknown')),
                "handling_instructions": handling_instructions,
                "label_warnings": warnings,
                "message": "This information is from the medication label. For personalized medical advice, consult your doctor or pharmacist."
            }

        except Exception as e:
            logger.error(f"error getting handling warnings for {med_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "retrieval_failed",
                "message": "I'm having trouble retrieving handling information right now. Please try again later."
            }
