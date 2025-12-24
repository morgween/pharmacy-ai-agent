"""pharmacy ai agent main application"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.domain.config import settings
from backend.routes import chat, auth
from backend.domain.logging_config import setup_logging
from backend.utils.security import SecurityMiddleware

logger = setup_logging(log_level="INFO", log_file="logs/pharmacy_agent.log")

app = FastAPI(
    title="Pharmacy AI Agent",
    description="AI-powered pharmacy assistant with user authentication",
    version="1.0.0"
)

app.add_middleware(SecurityMiddleware, enable_pii_masking=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)


@app.on_event("startup")
async def startup_validation():
    """validate critical resources at startup"""
    logger.info("=" * 60)
    logger.info("Starting Pharmacy AI Agent - Startup Validation")
    logger.info("=" * 60)

    errors = []

    if not settings.openai_api_key:
        errors.append("OPENAI_API_KEY not configured in environment")
        logger.error("❌ Missing OPENAI_API_KEY")
    else:
        logger.info("✅ OpenAI API key configured")

    if not os.path.exists(settings.medications_json_path):
        errors.append(f"Medications file not found: {settings.medications_json_path}")
        logger.error(f"❌ Missing medications.json at {settings.medications_json_path}")
    else:
        logger.info(f"✅ Medications file found: {settings.medications_json_path}")

    if not os.path.exists(settings.tool_schemas_dir):
        errors.append(f"Tool schemas directory not found: {settings.tool_schemas_dir}")
        logger.error(f"❌ Missing tool schemas directory: {settings.tool_schemas_dir}")
    else:
        missing_tools = []
        for tool_file in settings.allowed_tools:
            tool_path = os.path.join(settings.tool_schemas_dir, tool_file)
            if not os.path.exists(tool_path):
                missing_tools.append(tool_file)

        if missing_tools:
            errors.append(f"Missing tool schemas: {', '.join(missing_tools)}")
            logger.error(f"❌ Missing tool schemas: {missing_tools}")
        else:
            logger.info(f"✅ All {len(settings.allowed_tools)} tool schemas found")

    user_db_dir = os.path.dirname(settings.user_db_path)
    if user_db_dir and not os.path.exists(user_db_dir):
        logger.warning(f"⚠️  User database directory doesn't exist, will be created: {user_db_dir}")
        os.makedirs(user_db_dir, exist_ok=True)

    logger.info(f"✅ User database path: {settings.user_db_path}")

    logger.info(f"Configuration:")
    logger.info(f"  - Model: {settings.openai_model}")
    logger.info(f"  - Temperature: {settings.openai_temperature}")
    logger.info(f"  - Data source: {settings.medication_data_source}")
    logger.info(f"  - Inventory service: {settings.inventory_service_url}")
    logger.info(f"  - Port: {settings.port}")

    if errors:
        logger.error("=" * 60)
        logger.error("STARTUP FAILED - Critical errors found:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("=" * 60)
        raise RuntimeError(f"Startup validation failed: {'; '.join(errors)}")

    logger.info("=" * 60)
    logger.info("✅ Startup validation complete - All systems ready")
    logger.info("=" * 60)


@app.get("/")
async def root():
    """root endpoint returns api status"""
    return {"message": "Pharmacy AI Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    """health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)