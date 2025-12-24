"""openai client wrapper and prompt builder"""
import logging
from typing import Dict, List
from openai import AsyncOpenAI

from backend.domain.config import settings
from backend.prompts import build_system_prompt

logger = logging.getLogger(__name__)


class OpenAIClient:
    """wrap openai client and prompt caching"""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info("openai client initialized successfully")
        self._system_prompt_cache: Dict[str, str] = {}

    def build_system_prompt(self, knowledge_base: List[dict], language: str = "en") -> str:
        """build system prompt with caching"""
        if language in self._system_prompt_cache:
            logger.debug(f"using cached system prompt for language: {language}")
            return self._system_prompt_cache[language]

        prompt = build_system_prompt(knowledge_base, language)
        self._system_prompt_cache[language] = prompt
        logger.info(
            f"built and cached system prompt with {len(knowledge_base)} medications for language: {language}"
        )
        return prompt
