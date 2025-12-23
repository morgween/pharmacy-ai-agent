"""tool schema registry for pharmacy ai agent"""
import json
import logging
import os
from typing import List, Dict, Iterable

logger = logging.getLogger(__name__)


def load_tool_schemas(
    allowed_tools: Iterable[str],
    tool_schemas_dir: str
) -> List[Dict]:
    """
    load tool schemas from the configured directory with error handling

    args:
        allowed_tools: iterable of tool schema filenames
        tool_schemas_dir: directory path containing tool schema files

    returns:
        list of tool schema dictionaries

    raises:
        RuntimeError: if no tool schemas could be loaded
    """
    schemas: List[Dict] = []

    for filename in allowed_tools:
        filepath = os.path.join(tool_schemas_dir, filename)

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
            continue
        except Exception as e:
            logger.error(f"error loading tool schema {filename}: {e}")
            continue

    if not schemas:
        logger.error("no tool schemas loaded - agent will have no tools!")
        raise RuntimeError("critical: no tool schemas available")

    logger.info(f"loaded {len(schemas)} tool schemas")
    return schemas
