"""centralized configuration for pharmacy ai agent"""
import os
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List, Union, Optional
from backend.constants import ALLOWED_TOOL_SCHEMAS

class Settings(BaseSettings):
    """application configuration settings loaded from environment variables"""

    # api keys
    openai_api_key: str

    # server configuration
    port: int = 8000

    frontend_origin: str = "http://localhost:3000"
    allowed_origins: Optional[Union[List[str], str]] = None

    # data source configuration
    medication_data_source: str = "api"

    # openai configuration
    openai_model: str = "gpt-5-mini"
    openai_temperature: float = 1.0
    openai_timeout: float = 20.0

    # external service urls
    inventory_service_url: str = "http://127.0.0.1:8001"
    medication_service_url: str = "http://127.0.0.1:8002"

    # data paths
    medications_json_path: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "medications.json"
    )
    medications_db_path: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "medications.db"
    )
    user_db_path: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "users.db"
    )
    users_json_path: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "demo_users.json"
    )

    inventory_json_path: str = os.path.join(
        os.path.dirname(__file__), "..", "demo_server_app", "data", "inventory.json"
    )

    # tool schemas directory
    tool_schemas_dir: str = os.path.join(
        os.path.dirname(__file__), "..", "open_ai_tool_schemas"
    )

    # allowed tool schemas
    allowed_tools: List[str] = list(ALLOWED_TOOL_SCHEMAS)

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """
        parse comma-separated CORS origins from environment variable

        args:
            v: string or list of allowed origins

        returns:
            list of origin strings
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @model_validator(mode='after')
    def set_default_allowed_origins(self):
        """ensure CORS matches configured frontend origin when list is not provided"""
        if not self.allowed_origins:
            self.allowed_origins = self.parse_cors_origins(self.frontend_origin)
        return self

    class Config:
        env_file = ".env"

settings = Settings()
