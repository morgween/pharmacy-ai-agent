"""openai service for pharmacy ai agent with function calling"""
import logging
from typing import List, Dict, Any, Optional
from backend.domain.config import settings
from backend.tool_framework.registry import load_tool_schemas
from backend.tool_framework.executor import ToolExecutor
from backend.services.agent_tools import AgentTools
from backend.services.agent_utils import load_static_json, format_ambiguous_response
from backend.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# module-level singleton instance
_service_instance: Optional["OpenAIAgentService"] = None


def get_openai_service() -> "OpenAIAgentService":
    """
    get singleton instance of openai agent service

    returns:
        cached OpenAIAgentService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = OpenAIAgentService()
    return _service_instance


class OpenAIAgentService:
    """service for openai agent with function calling and medication knowledge base"""

    def __init__(self):
        """initialize openai agent service with client, tools, and cached data"""
        try:
            self.openai_client = OpenAIClient()

            # use configured data source (api or db)
            if settings.medication_data_source == "db":
                from backend.data_sources.medications_db import MedicationsDB
                self.medications_api = MedicationsDB()
                logger.info("using medications database as data source")
            else:
                from backend.data_sources.medications_api import MedicationsAPI
                self.medications_api = MedicationsAPI()
                logger.info("using medications api (json file) as data source")

            self.tools = load_tool_schemas(settings.allowed_tools, settings.tool_schemas_dir)

            # cache static json data at initialization
            self._pharmacy_locations = load_static_json("pharmacy_locations.json")
            logger.info("cached pharmacy_locations")

            # cache user database instance
            from backend.models.user import UserDatabase
            self._user_db = UserDatabase()
            logger.info("cached user database instance")

            self._agent_tools = AgentTools(
                medications_api=self.medications_api,
                user_db=self._user_db,
                pharmacy_locations=self._pharmacy_locations,
                format_ambiguous_response=format_ambiguous_response
            )
            self.tool_executor = ToolExecutor(self._agent_tools)

            logger.info(f"openai agent service initialized with {len(self.tools)} tools")

        except Exception as e:
            logger.error(f"failed to initialize openai agent service: {e}")
            raise RuntimeError(f"critical: failed to initialize agent service: {e}")

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
        return await self.tool_executor.execute(function_name, arguments)

    def build_system_prompt(self, language: str = 'en') -> str:
        """
        build system prompt with embedded medication knowledge base and caching

        args:
            language: language code for medication names and details

        returns:
            cached system prompt string with policies and available tools
        """
        try:
            knowledge_base = self.medications_api.get_all_medications(language)
            return self.openai_client.build_system_prompt(knowledge_base, language)
        except Exception as e:
            logger.error(f"error building system prompt: {e}", exc_info=True)
            logger.warning("using minimal system prompt with empty knowledge base")
            return self.openai_client.build_system_prompt([], language)
